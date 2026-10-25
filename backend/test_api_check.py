import requests

BASE_URL = 'http://127.0.0.1:8000/api'
login_res = requests.post(f'{BASE_URL}/auth/login', json={'email': 'admin@example.com', 'password': 'AdminPassword123!'})
print('Login status:', login_res.status_code)
if login_res.status_code == 200:
    token = login_res.json()['data']['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    stus_res = requests.get(f'{BASE_URL}/admin/students?page=1&pageSize=10', headers=headers)
    print('Admin students status:', stus_res.status_code)
    if stus_res.status_code == 200:
        data = stus_res.json()['data']
        items = data.get('items', [])
        total = data.get('total')
        print(f'Total students: {total}, items count: {len(items)}')
        for s in items[:6]:
            print(f"  Roll: {s.get('rollNumber')}, Batch: {s.get('batch')}, Year: {s.get('year')}, Sec: {s.get('section')}")

    years_res = requests.get(f'{BASE_URL}/mentor/students/years', headers=headers)
    print('Mentor years status:', years_res.status_code)
    if years_res.status_code == 200:
        for y in years_res.json()['data']:
            print('  Year Card:', y)

    for yr in ['4th Year', '3rd Year', '2nd Year']:
        secs_res = requests.get(f'{BASE_URL}/mentor/students/sections?year={yr}', headers=headers)
        if secs_res.status_code == 200:
            secs = secs_res.json()['data']
            print(f'Section cards for {yr} ({len(secs)} sections):')
            for sc in secs:
                print(f"    Section: {sc.get('section')}, Students: {sc.get('studentCount')}")
