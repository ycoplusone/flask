
# 가상화 수행
source ~/flask/.venv/bin/activate

# flask 실행
python ~/flask/run.py

# wsl 삭제된 파일 특정폴더로 복원
find ~/.vscode-server/data/User/History/ -type f \( -name "*.py" -o -name "*.html" -o -name "*.md" \) -exec sh -c 'for f; do dir=$(dirname "$f"); if grep -q "flask" "$dir/entries.json" 2>/dev/null; then echo "$f"; fi; done' _ {} + | xargs -I {} cp {} ~/flask/recovered_files/ 2>/dev/null

# vscode 히스토리에서 일자별 원본파일별로 백업자료 리스트 찾기
find ~/.vscode-server/data/User/History/ -type f -name "*.html" -exec sh -c '
for f; do
  dir=$(dirname "$f")
  if [ -f "$dir/entries.json" ] && grep -q "flask" "$dir/entries.json" 2>/dev/null; then
    orig=$(grep -o "\"resource\":\"[^\"]*\"" "$dir/entries.json" | head -n 1 | sed "s/\"resource\":\"file:\/\///;s/\"//g")
    ctime=$(stat -c "%z" "$f" 2>/dev/null | cut -d"." -f1)
    echo "$ctime | 원본: $orig | 백업: $f"
  fi
done
' _ {} + | sort -r
;