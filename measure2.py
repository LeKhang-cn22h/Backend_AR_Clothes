import time, requests, base64

FITDIT_URL = "http://localhost:7860"
person_path = "femal.jpg"
cloth_path  = "cloth.jpg"

def img_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def measure(num_steps):
    start = time.time()
    resp = requests.post(f"{FITDIT_URL}/submit", json={
        "person_image":  img_to_b64(person_path),
        "garment_image": img_to_b64(cloth_path),
        "category": "upper", "num_steps": num_steps,
        "guidance_scale": 2.0, "resolution": "768x1024",
    })
    job_id = resp.json()["job_id"]
    print(f"  job_id: {job_id[:8]}")
    while True:
        r = requests.get(f"{FITDIT_URL}/status/{job_id}").json()
        print(f"  {r['status']} ({r.get('elapsed_s',0):.1f}s)")
        if r["status"] == "done":
            print(f"  inference_time_s: {r['inference_time_s']}s")
            return r["inference_time_s"]
        if r["status"] == "failed":
            return None
        time.sleep(5)

for steps in [20, 25]:
    times = []
    print(f"\n--- num_steps={steps} ---")
    for run in range(3):
        print(f"  [Lần {run+1}]")
        t = measure(steps)
        if t: times.append(t)
        if run < 2:
            print("  Nghỉ 30s...")
            time.sleep(30)
    if times:
        print(f"  Trung bình: {round(sum(times)/len(times),2)}s")
        print(f"  Chi tiết: {times}")
    print("Nghỉ 60s...")
    time.sleep(60)