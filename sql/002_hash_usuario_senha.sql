-- Supabase/PostgreSQL: transforme a senha em bcrypt antes de gravar a linha.
-- Rode uma vez no SQL Editor do Supabase antes de inserir/atualizar usuarios.
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

DO $check_extension$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_extension e
        JOIN pg_namespace n ON n.oid = e.extnamespace
        WHERE e.extname = 'pgcrypto' AND n.nspname = 'extensions'
    ) THEN
        RAISE EXCEPTION 'Instale pgcrypto no schema extensions antes de aplicar esta migration.';
    END IF;
END;
$check_extension$;

CREATE OR REPLACE FUNCTION public.hash_usuario_senha()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, extensions
AS $function$
BEGIN
    IF NEW.senha_hash IS NULL OR BTRIM(NEW.senha_hash) = '' THEN
        RAISE EXCEPTION 'A senha nao pode ficar vazia.';
    END IF;

    -- Mantem hashes ja gerados pelo Werkzeug ou pelo proprio pgcrypto.
    IF NEW.senha_hash LIKE '$2a$%'
       OR NEW.senha_hash LIKE '$2b$%'
       OR NEW.senha_hash LIKE '$2y$%'
       OR NEW.senha_hash LIKE 'scrypt:%$%$%'
       OR NEW.senha_hash LIKE 'pbkdf2:%$%$%' THEN
        RETURN NEW;
    END IF;

    -- bcrypt do pgcrypto aceita no maximo 72 bytes; impede truncamento silencioso.
    IF octet_length(NEW.senha_hash) > 72 THEN
        RAISE EXCEPTION 'A senha excede o limite de 72 bytes do bcrypt.';
    END IF;

    NEW.senha_hash := extensions.crypt(NEW.senha_hash, extensions.gen_salt('bf', 12));
    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS usuario_hash_senha_insert ON public.usuario;
CREATE TRIGGER usuario_hash_senha_insert
BEFORE INSERT ON public.usuario
FOR EACH ROW EXECUTE FUNCTION public.hash_usuario_senha();

DROP TRIGGER IF EXISTS usuario_hash_senha_update ON public.usuario;
CREATE TRIGGER usuario_hash_senha_update
BEFORE UPDATE OF senha_hash ON public.usuario
FOR EACH ROW EXECUTE FUNCTION public.hash_usuario_senha();

-- Converte valores antigos em texto puro sem alterar hashes ja reconhecidos.
UPDATE public.usuario
SET senha_hash = senha_hash
WHERE senha_hash IS NOT NULL
  AND BTRIM(senha_hash) <> ''
  AND senha_hash NOT LIKE '$2a$%'
  AND senha_hash NOT LIKE 'scrypt:%$%$%'
  AND senha_hash NOT LIKE 'pbkdf2:%$%$%';
