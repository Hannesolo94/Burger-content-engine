-- Burger Content Engine backend (Oct 23 2026). Paste this whole file into the Supabase SQL editor and press Run, once.
-- Same safety model as CRAFT: RLS on with zero policies, so the public key reaches nothing on its own.
-- Every read/write goes through security-definer functions that demand the owner token (only its sha256 is stored here).

create table if not exists public.app_owner (token_sha text primary key);
create table if not exists public.engine (id text primary key, data jsonb not null, updated_at timestamptz not null default now());
create table if not exists public.state  (key text primary key, value jsonb, updated_at timestamptz not null default now());
alter table public.app_owner enable row level security;
alter table public.engine    enable row level security;
alter table public.state     enable row level security;

insert into public.app_owner(token_sha) values ('6a6a7092223ca6ad50587a64dcdb8500f3e2d59c13077e1fbc31100f6c4756ea') on conflict do nothing;

create or replace function public.be_ok(p_token text) returns boolean
language sql security definer set search_path = public, extensions as $$
  select exists(select 1 from app_owner where token_sha = encode(extensions.digest(p_token, 'sha256'), 'hex'));
$$;

-- everything the site needs in one call: the content (what data.js used to hold) and every saved state blob
create or replace function public.be_get(p_token text) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  if not be_ok(p_token) then raise exception 'nope'; end if;
  return jsonb_build_object(
    'engine', (select data from engine where id = 'main'),
    'state',  coalesce((select jsonb_object_agg(key, jsonb_build_object('v', value, 't', updated_at)) from state), '{}'::jsonb));
end $$;

create or replace function public.be_put(p_token text, p_key text, p_value jsonb) returns timestamptz
language plpgsql security definer set search_path = public as $$
declare t timestamptz := now();
begin
  if not be_ok(p_token) then raise exception 'nope'; end if;
  if p_key !~ '^burger-engine-[a-z0-9-]+$' then raise exception 'bad key'; end if;
  insert into state(key, value, updated_at) values (p_key, p_value, t)
    on conflict (key) do update set value = excluded.value, updated_at = t;
  return t;
end $$;

-- content push from tools/push_engine.py, same token gate, so no secret key is ever needed
create or replace function public.be_put_engine(p_token text, p_data jsonb) returns timestamptz
language plpgsql security definer set search_path = public as $$
declare t timestamptz := now();
begin
  if not be_ok(p_token) then raise exception 'nope'; end if;
  insert into engine(id, data, updated_at) values ('main', p_data, t)
    on conflict (id) do update set data = excluded.data, updated_at = t;
  return t;
end $$;

revoke all on function public.be_ok(text) from public, anon, authenticated;
grant execute on function public.be_get(text) to anon;
grant execute on function public.be_put(text, text, jsonb) to anon;
grant execute on function public.be_put_engine(text, jsonb) to anon;
