#!/usr/bin/env bash
set -euo pipefail

cd /home/thaidz/Projects/Tool-VBPL-Scraper

types=(
  hien_phap
  bo_luat
  luat
  phap_lenh
  nghi_dinh
  thong_tu
  quyet_dinh
  lenh
  nghi_quyet
  nghi_quyet_lien_tich
  van_ban_hop_nhat
  van_ban_hanh_chinh_lien_quan
  ban_dich_van_ban
  chi_thi
  van_ban_he_thong_hoa
  chua_xac_dinh
  thong_tu_lien_tich
  thong_tu_lien_bo
  cong_uoc
  thong_bao
  van_ban_khac
  sac_luat
  quy_dinh
  sac_lenh
  cong_van
  van_ban_lien_quan
)

for type_id in "${types[@]}"; do
  echo "===== $(date '+%F %T') FILL ${type_id} ====="
  docker compose run -T --rm vbpl-crawler python crawler_vbpl.py --type-id "${type_id}" --all-pages --page-size 10
  echo "===== $(date '+%F %T') DONE ${type_id} ====="
done
