"""Testes automatizados de ponta a ponta do sistema de medicamentos e comandos de estoque."""

import sys
import uuid
from fastapi.testclient import TestClient

from presentation.main import app

client = TestClient(app)


def test_complete_medication_and_stock_flow() -> None:
    """Valida o ciclo completo de cadastro de medicamentos e comandos de movimentação de estoque."""
    print("=" * 75)
    print(" INICIANDO TESTES DO SISTEMA DE MEDICAMENTOS E COMANDOS DE ESTOQUE")
    print("=" * 75)

    unique_suffix = uuid.uuid4().hex[:6]
    med_name = f"Paracetamol Teste {unique_suffix}"
    med_dosage = "750mg"

    # 1. Teste de Cadastro de Medicamento com Comando Automático de Estoque Inicial
    print(f"\n[1/8] Testando cadastro de medicamento '{med_name}' com estoque inicial 50...")
    payload_create = {
        "name": med_name,
        "dosage": med_dosage,
        "unit": "comprimido",
        "initial_stock": 50,
        "minimum_stock": 15,
        "description": "Analgésico e antitérmico para teste de fluxo de estoque.",
    }
    res = client.post("/api/v1/medications/", json=payload_create)
    assert res.status_code == 201, f"Falha no cadastro de medicamento: {res.status_code} - {res.text}"
    med_data = res.json()
    med_id = med_data["id"]
    assert med_data["name"] == med_name
    assert med_data["dosage"] == med_dosage
    assert med_data["current_stock"] == 50
    assert med_data["minimum_stock"] == 15
    assert med_data["stock_status"] == "OK"
    print(f"  -> Medicamento cadastrado com sucesso! ID: {med_id} | Saldo: {med_data['current_stock']}")

    # 2. Teste de Verificação do Histórico de Estoque Inicial Automático
    print("\n[2/8] Verificando se o comando de movimentação inicial foi registrado automaticamente...")
    res = client.get(f"/api/v1/medications/{med_id}/movements")
    assert res.status_code == 200, f"Falha ao consultar movimentações: {res.status_code}"
    movements = res.json()
    assert len(movements) == 1
    init_mov = movements[0]
    assert init_mov["movement_type"] == "ENTRADA"
    assert init_mov["quantity"] == 50
    assert init_mov["previous_stock"] == 0
    assert init_mov["new_stock"] == 50
    print(f"  -> Movimentação de estoque inicial confirmada: {init_mov['movement_type']} +{init_mov['quantity']} (Saldo: {init_mov['new_stock']})")

    # 3. Teste de Comando de Atualização de Estoque (ENTRADA)
    print("\n[3/8] Testando comando de atualização de estoque (ENTRADA +30)...")
    res = client.post(
        f"/api/v1/medications/{med_id}/stock",
        json={
            "movement_type": "ENTRADA",
            "quantity": 30,
            "reason": "Chegada de novo lote de farmácia",
        },
    )
    assert res.status_code == 200, f"Falha no comando ENTRADA: {res.status_code} - {res.text}"
    mov_in = res.json()
    assert mov_in["previous_stock"] == 50
    assert mov_in["quantity"] == 30
    assert mov_in["new_stock"] == 80
    print(f"  -> Comando ENTRADA executado: 50 -> 80 unidades.")

    # 4. Teste de Comando de Atualização de Estoque (SAIDA)
    print("\n[4/8] Testando comando de atualização de estoque (SAÍDA -70)...")
    res = client.post(
        f"/api/v1/medications/{med_id}/stock",
        json={
            "movement_type": "SAIDA",
            "quantity": 70,
            "reason": "Administração para paciente febril",
        },
    )
    assert res.status_code == 200, f"Falha no comando SAIDA: {res.status_code} - {res.text}"
    mov_out = res.json()
    assert mov_out["previous_stock"] == 80
    assert mov_out["quantity"] == 70
    assert mov_out["new_stock"] == 10  # Abaixo do mínimo de 15 -> deve virar LOW
    print(f"  -> Comando SAÍDA executado: 80 -> 10 unidades.")

    # 5. Teste de Verificação do Status de Criticidade de Estoque (LOW)
    print("\n[5/8] Verificando classificação de estoque baixo (Saldo 10 <= Mínimo 15)...")
    res = client.get(f"/api/v1/medications/{med_id}")
    assert res.status_code == 200
    med_detail = res.json()
    assert med_detail["current_stock"] == 10
    assert med_detail["stock_status"] == "LOW"
    print(f"  -> Status de estoque classificado corretamente como LOW!")

    # 6. Teste de Bloqueio Contra Saldo Negativo (Tentativa de saída maior que estoque)
    print("\n[6/8] Testando proteção contra saldo negativo (tentar retirar 50 quando saldo é 10)...")
    res = client.post(
        f"/api/v1/medications/{med_id}/stock",
        json={
            "movement_type": "SAIDA",
            "quantity": 50,
            "reason": "Tentativa indevida de retirada além do saldo",
        },
    )
    assert res.status_code == 400, f"Esperado 400 para saldo insuficiente, obtido {res.status_code}"
    print(f"  -> Operação bloqueada com sucesso (HTTP 400): {res.json()['message']}")

    # 7. Teste de Atualização de Dados Cadastrais (PUT)
    print("\n[7/8] Testando atualização dos dados cadastrais (PUT /medications/{id})...")
    updated_name = f"{med_name} Forte"
    updated_payload = {
        "name": updated_name,
        "dosage": "1000mg",
        "unit": "comprimido",
        "minimum_stock": 20,
        "description": "Fórmula potencializada para testes atualizados."
    }
    res = client.put(f"/api/v1/medications/{med_id}", json=updated_payload)
    assert res.status_code == 200, f"Falha no PUT de medicamento: {res.status_code} - {res.text}"
    updated_data = res.json()
    assert updated_data["name"] == updated_name
    assert updated_data["dosage"] == "1000mg"
    assert updated_data["minimum_stock"] == 20
    assert updated_data["description"] == "Fórmula potencializada para testes atualizados."
    assert updated_data["updated_at"] is not None
    print(f"  -> Dados cadastrais atualizados com sucesso via PUT: '{updated_data['name']}' ({updated_data['dosage']})")

    # 8. Teste de Atualização Parcial dos Dados Cadastrais (PATCH)
    print("\n[8/9] Testando atualização parcial de dados cadastrais (PATCH /medications/{id})...")
    patch_payload = {
        "description": "Descrição refinada via PATCH parcial."
    }
    res = client.patch(f"/api/v1/medications/{med_id}", json=patch_payload)
    assert res.status_code == 200, f"Falha no PATCH de medicamento: {res.status_code} - {res.text}"
    patch_data = res.json()
    assert patch_data["name"] == updated_name  # Mantido
    assert patch_data["dosage"] == "1000mg"    # Mantido
    assert patch_data["description"] == "Descrição refinada via PATCH parcial."
    print("  -> Atualização parcial via PATCH executada com sucesso!")

    # 9. Teste de Interpretação de QR Code (Medicamento Existente + Novo Medicamento)
    print("\n[9/10] Testando resolução de QR Code (POST /medications/qrcode/resolve)...")
    res_qr_existing = client.post(
        "/api/v1/medications/qrcode/resolve",
        json={"raw_data": f'{{"id": "{med_id}", "name": "{updated_name}", "dosage": "1000mg"}}'},
    )
    assert res_qr_existing.status_code == 200, f"Falha no resolve de QR existente: {res_qr_existing.text}"
    qr_existing_data = res_qr_existing.json()
    assert qr_existing_data["found"] is True
    assert qr_existing_data["medication"]["id"] == med_id

    res_qr_new = client.post(
        "/api/v1/medications/qrcode/resolve",
        json={"raw_data": "Amoxicilina|500mg|capsula|30|10|Antibiótico"},
    )
    assert res_qr_new.status_code == 200, f"Falha no resolve de QR novo: {res_qr_new.text}"
    qr_new_data = res_qr_new.json()
    assert qr_new_data["found"] is False
    assert qr_new_data["parsed_data"]["name"] == "Amoxicilina"
    assert qr_new_data["parsed_data"]["dosage"] == "500mg"
    assert qr_new_data["parsed_data"]["unit"] == "capsula"
    print("  -> Resolução de QR Code (JSON e Pipe) validada com sucesso!")

    # 10. Teste de Lotes, Validade (FEFO), Bloqueio de Vencidos e LEDs Arduino
    print("\n[10/11] Testando Lotes (ex: 50 caixas), Validade FEFO, Bloqueio de Vencidos e LEDs Arduino...")
    res_lote_valido = client.post(
        f"/api/v1/medications/{med_id}/batches",
        json={
            "batch_number": "LOTE-2027-OK",
            "quantity": 50,
            "expiration_date": "2027-12-31",
            "reason": "Chegada de lote com 50 caixas",
        },
    )
    assert res_lote_valido.status_code == 201, f"Falha ao criar lote válido: {res_lote_valido.text}"
    lote_ok_data = res_lote_valido.json()
    assert lote_ok_data["batch_number"] == "LOTE-2027-OK"
    assert lote_ok_data["quantity"] == 50
    assert lote_ok_data["is_expired"] is False
    assert lote_ok_data["expiration_status"] == "VALID"

    # Cadastra um lote vencido para testar o bloqueio de segurança e o LED Vermelho
    res_lote_vencido = client.post(
        f"/api/v1/medications/{med_id}/batches",
        json={
            "batch_number": "LOTE-2020-VENC",
            "quantity": 15,
            "expiration_date": "2020-01-10",
            "reason": "Lote antigo vencido para teste de bloqueio",
        },
    )
    assert res_lote_vencido.status_code == 201, f"Falha ao criar lote vencido: {res_lote_vencido.text}"
    lote_venc_data = res_lote_vencido.json()
    assert lote_venc_data["is_expired"] is True
    assert lote_venc_data["expiration_status"] == "EXPIRED"

    # Verifica se o medicamento acusa LED RED por possuir lote vencido ativo
    res_med_led = client.get(f"/api/v1/medications/{med_id}")
    assert res_med_led.status_code == 200
    med_led_data = res_med_led.json()
    assert med_led_data["alert_led"] == "RED"
    assert med_led_data["expired_stock"] == 15

    # Tenta dar baixa diretamente no lote vencido -> deve ser BLOQUEADO (HTTP 400)
    res_baixa_vencido = client.post(
        f"/api/v1/medications/{med_id}/stock",
        json={
            "movement_type": "SAIDA",
            "quantity": 5,
            "batch_number": "LOTE-2020-VENC",
            "reason": "Tentativa de dispensar lote vencido",
        },
    )
    assert res_baixa_vencido.status_code == 400, "Deveria bloquear saída de lote vencido!"
    print(f"  -> Bloqueio de lote vencido funcionando (LED RED): {res_baixa_vencido.json()['message']}")

    # 11. Teste de Exclusão de Cadastro (DELETE /medications/{id})
    print("\n[11/11] Testando exclusão do cadastro (DELETE /medications/{id})...")
    res_del = client.delete(f"/api/v1/medications/{med_id}")
    assert res_del.status_code == 200, f"Falha ao apagar medicamento: {res_del.status_code} - {res_del.text}"
    del_data = res_del.json()
    assert del_data["id"] == med_id
    print(f"  -> {del_data['message']}")

    # Confirma que não existe mais no banco (deve retornar 400 ValueError de não encontrado)
    res_check = client.get(f"/api/v1/medications/{med_id}")
    assert res_check.status_code == 400
    print("  -> Confirmado: registro removido do catálogo com sucesso!")

    print("\n" + "=" * 75)
    print(" TODOS OS 10 TESTES DE MEDICAMENTOS, ESTOQUE, QR CODE E EXCLUSÃO PASSARAM!")
    print("=" * 75)


if __name__ == "__main__":
    try:
        test_complete_medication_and_stock_flow()
    except Exception as e:
        print(f"\nERRO NO TESTE: {e}")
        sys.exit(1)
