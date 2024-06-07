import pandas as pd
jumlahdata = 4
df = pd.read_excel('nominatiff.xlsx', sheet_name='Lokal', nrows=jumlahdata)
# df['harian'] = df['harian'].astype(int)
mak = (df['MAK'][0])
nama_keg = (df['nama_keg'][0])
tgl_keg = (df['tgl_keg'][0])
lok_keg = (df['lok_keg'][0])

daftarNominatif = []
for r_idx, r_val in df.iterrows():
    nama = r_val['NAMA']
    asal = r_val['ASAL']
    tujuan = r_val['TUJUAN']
    pesawat = r_val['PESAWAT']
    ta = r_val['TA']
    tt = r_val['TT']
    p = r_val['p']
    p_p = r_val['p_p']
    penginapan = r_val['PENGINAPAN']
    h = r_val['h']
    h_h = r_val['h_h']
    harian = r_val['HARIAN']
    total = r_val['TOTAL']
    # tgl_st = kalender_indo(r_val['tgl_st'])
    # tgl_tugas = kalender_indo(r_val['tgl_tugas'])
    # kali = r_val['kali']
    # harian = r_val['harian']
    # uang = rupiah_strip(r_val['uang'])
    daftarNominatif.append({"no": str(r_idx+1), "NAMA": nama, "asal": asal, "tujuan": tujuan, "pesawat": pesawat, "ta": ta, "tt": tt, "p": p, "l": p, "p_p": p_p, "penginapan": penginapan, "h": h, "h_h": h_h, "harian": harian, "total":total})   

print(daftarNominatif)