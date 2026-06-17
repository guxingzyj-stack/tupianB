"""/api/upload 测试。"""


def test_upload_returns_url(client, test_image_b64):
    r = client.post("/api/upload", json={"device_id": "dev-up", "image": test_image_b64})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["image_url"].endswith(".jpg")
    assert body["upload_id"].startswith("u_")


def test_upload_bad_image(client):
    r = client.post("/api/upload", json={"device_id": "d", "image": "@@not-base64@@"})
    assert r.status_code == 400
