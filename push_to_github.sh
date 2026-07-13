#!/bin/bash
# Yem Qarz Daftari ni GitHub'ga yuklash uchun tayyor skript.
# Tokenni chatga YOZMANG - bu skript uni faqat terminalda sorgaydi.
#
# Ishlatish:
#   1) GitHub'da yangi PRIVATE repo oching (masalan: yem-qarz-bot)
#   2) Quyidagi 2 ta o'zgaruvchini to'ldiring:
REPO_NAME="yem-qarz-bot"          # <-- GitHub'dagi repo nomi
GITHUB_USER="your_username"        # <-- GitHub username
#   3) Yangi token oling: GitHub -> Settings -> Developer settings -> PAT
#      (faqat 'repo' huquqi). Uni quyidagi o'rniga YOZMANG, balki terminalda kiritasiz.
#
# XAVFSIZLIK: tokenni faylga yozmang. Quyidagi satr sizdan so'raydi.
read -s -p "GitHub PAT (token) kiriting: " TOKEN
echo ""
if [ -z "$TOKEN" ]; then
  echo "Token kiritilmadi. Chiqildi."
  exit 1
fi

REMOTE="https://$GITHUB_USER:$TOKEN@github.com/$GITHUB_USER/$REPO_NAME.git"
git remote remove origin 2>/dev/null
git remote add origin "$REMOTE"
git branch -M main
git push -u origin main
echo ""
echo "✅ Yuklandi: https://github.com/$GITHUB_USER/$REPO_NAME"
echo "⚠️  Pushdan keyin tokenni GitHub'da revoke qiling (xavfsizlik uchun)."
