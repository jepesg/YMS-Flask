-- Adiciona os campos de identidade visual usados pelo cabeçalho multiempresa.
ALTER TABLE public.empresa
    ADD COLUMN IF NOT EXISTS nome_empresa_seguranca VARCHAR(100),
    ADD COLUMN IF NOT EXISTS logo_empresa_seguranca VARCHAR(500),
    ADD COLUMN IF NOT EXISTS logo_empresa_portaria VARCHAR(500);
