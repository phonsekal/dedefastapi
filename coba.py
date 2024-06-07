import pandas as pd

df = pd.read_excel('nominatiff.xlsx', sheet_name='Nominatiff')
df['harian'] = df['harian'].astype(int)
daftarNominatif = []
mak = df['mak'][0]
mak1 = df['mak'][1]
total_harian = 0
for r_idx, r_val in df.iterrows():
    nama = r_val['nama']
    no_st = r_val['no_st']
    tgl_st = r_val['tgl_st']
    tgl_tugas = r_val['tgl_tugas']
    kali = r_val['kali']
    harian = r_val['harian']
    uang = r_val['uang']
    daftarNominatif.append({"no": str(r_idx+1), "nama": nama, "no_st": no_st, "tgl_st": tgl_st, "tgl_tugas": tgl_tugas, "kali": kali, "harian": harian, "uang": uang})   
    total_harian += harian  

print(mak) 
print(mak1) 