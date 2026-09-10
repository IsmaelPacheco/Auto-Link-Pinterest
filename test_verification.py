"""
test_verification.py
Script de verificação automatizada para todos os componentes do AutoLink Pinterest.
"""
import os
import sys
from pathlib import Path
from PIL import Image

# Força codificação UTF-8 no stdout do Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def run_tests():
    print("=== TESTES DE INTEGRACAO DO AUTOLINK PINTEREST ===")
    
    # 1. Teste ConfigManager
    print("\n[1/5] Testando ConfigManager...")
    from src.models.config_manager import ConfigManager
    cfg = ConfigManager()
    assert cfg.get("dark_mode") is not None
    assert cfg.get("max_pins_per_day") == 12
    print("[OK] ConfigManager OK!")

    # 2. Teste Database
    print("\n[2/5] Testando Database (SQLite)...")
    from src.models.database import Database
    db = Database()
    # Adiciona pin de teste
    test_id = "test_item_999"
    db.add_pin(
        shopee_item_id=test_id,
        title="Produto Teste",
        affiliate_link="https://s.shopee.com.br/test",
        original_price=100.0,
        discount_price=59.9,
        pinterest_url="https://pinterest.com/pin/123",
        status="SUCCESS"
    )
    assert db.is_already_posted(test_id) == True
    assert db.is_already_posted("item_nao_existente") == False
    pins = db.get_all_pins(limit=5)
    assert len(pins) > 0
    print(f"[OK] Database OK! Total pins no banco: {len(pins)}")

    # 3. Teste CopyEngine
    print("\n[3/5] Testando CopyEngine...")
    from src.engines.copy_engine import CopyEngine
    copy_engine = CopyEngine(use_gemini=False)
    prod_sample = {
        "title": "Mini Processador Manual de Alimentos 3 Lâminas Inox",
        "original_price": 49.90,
        "discount_price": 19.90,
        "discount_pct": 60
    }
    title, desc = copy_engine.generate_copy(prod_sample)
    print(f"  Titulo gerado: {title}")
    print(f"  Descricao gerada:\n{desc[:120]}...")
    assert len(title) > 5 and len(title) <= 100
    assert len(desc) > 20 and len(desc) <= 800
    assert "#" in desc
    print("[OK] CopyEngine OK!")

    # 4. Teste PinImageEngine (Pillow 1000x1500)
    print("\n[4/5] Testando PinImageEngine (Pillow 1000x1500)...")
    from src.engines.pin_image_engine import PinImageEngine
    img_engine = PinImageEngine()
    
    # Criar mock de download para testar localmente sem rede
    dummy_prod_img = Image.new("RGBA", (600, 600), (240, 100, 80, 255))
    img_engine.download_image = lambda url: dummy_prod_img
    
    generated_img = img_engine.create_pin_image(prod_sample)
    assert generated_img.size == (1000, 1500), f"Tamanho incorreto: {generated_img.size}"
    
    out_file = img_engine.save_pin_image(generated_img, "test_generated_pin")
    assert out_file.exists()
    assert out_file.stat().st_size > 1000
    print(f"[OK] PinImageEngine OK! Imagem gerada: {out_file.name} ({out_file.stat().st_size} bytes, 1000x1500 px)")

    # 5. Teste de Assinatura Shopee SHA256 Oficial e Busca
    print("\n[5/6] Testando Assinatura SHA256, Conexao Real e Busca na Shopee...")
    from src.engines.shopee_engine import ShopeeEngine
    shopee = ShopeeEngine(app_id=cfg.get("shopee_app_id"), secret=cfg.get("shopee_secret"))
    res_shopee = shopee.test_connection()
    print("  Resultado Conexao Shopee:", res_shopee)
    assert res_shopee["success"] == True, f"Falha Shopee: {res_shopee}"
    
    # Testar busca real por 'organizador'
    produtos = shopee.search_promotions("organizador", limit=3)
    print(f"  Encontrados {len(produtos)} produtos para 'organizador':")
    for p in produtos:
        print(f"    - {p['title'][:45]}... | R$ {p['discount_price']:.2f} ({p['discount_pct']}% OFF)")
    assert len(produtos) > 0, "Nenhum produto retornado na busca!"
    print("[OK] Shopee API Busca e Ofertas OK!")

    # 6. Teste PinVideoEngine (MP4 1000x1500)
    print("\n[6/6] Testando PinVideoEngine (MP4 vertical 1000x1500 animado)...")
    from src.engines.pin_video_engine import PinVideoEngine
    vid_engine = PinVideoEngine()
    dummy_prod_img = Image.new("RGBA", (600, 600), (240, 100, 80, 255))
    vid_engine.img_engine.download_image = lambda url: dummy_prod_img
    video_path = vid_engine.create_pin_video(prod_sample, filename_prefix="test_verification")
    assert video_path.exists(), "Arquivo de vídeo não foi criado!"
    assert video_path.stat().st_size > 5000, "Tamanho de vídeo muito pequeno!"
    print(f"[OK] PinVideoEngine OK! Video gerado: {video_path.name} ({video_path.stat().st_size} bytes, 1000x1500 px)")

    # Bonus. Teste de importação da GUI PySide6
    print("\n[Bonus] Testando importacao de todas as paginas da interface...")
    from src.views.main_window import MainWindow
    print("[OK] Importacao PySide6 e MainWindow OK!")

    print("\nTODOS OS TESTES PASSARAM COM 100% DE SUCESSO!")

if __name__ == "__main__":
    run_tests()

