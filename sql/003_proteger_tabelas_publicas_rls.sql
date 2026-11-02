-- Protege as tabelas expostas no schema public.
-- O Flask acessa o banco diretamente via DATABASE_URL. A conexão atual usa
-- um usuário Supabase postgres-prefixed, que deve manter o acesso de servidor.
-- anon/authenticated não recebem políticas porque a autenticação do sistema
-- é feita pelo Flask, não pelo Supabase Auth.

ALTER TABLE public.empresa ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usuario ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.veiculo ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doca ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.movimentacao ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE
    public.empresa,
    public.usuario,
    public.veiculo,
    public.doca,
    public.movimentacao
FROM anon, authenticated;
