# بوت Clash of Clans — Legend League Battle Log

البوت يأخذ Tag اللاعب عبر أمر Discord `/legend` ويحاول جلب سجل Legend League من ClashKing API، ثم يرسم صورة مستوحاة من النمط المرجعي: شريط علوي خمري، مربعات الهجمات، مربعات الدفاعات، النجوم، وتلخيص النقاط.

## المتطلبات
- Python 3.10 أو أحدث
- بوت Discord من Discord Developer Portal
- تفعيل `applications.commands` في رابط دعوة البوت
- اتصال بالإنترنت

## التشغيل على Windows
1. فك ضغط الملف.
2. ثبّت Python 3.10+ إذا لم يكن مثبتًا.
3. افتح المجلد، ثم اكتب `cmd` في شريط عنوان File Explorer واضغط Enter.
4. نفّذ:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
5. انسخ `.env.example` وسمّ النسخة `.env`.
6. افتح `.env` وضع توكن البوت بعد `DISCORD_TOKEN=`. لا ترسل التوكن لأي شخص.
7. شغّل:
   ```bat
   py bot.py
   ```
8. في Discord اكتب `/legend`، ثم أدخل Tag اللاعب. يمكن إدخال `day` إذا احتجت يومًا محددًا.

## إنشاء البوت ودعوته
- افتح https://discord.com/developers/applications
- New Application → Bot → Reset Token/Copy Token
- OAuth2 → URL Generator → اختر `bot` و `applications.commands`
- في صلاحيات البوت اختر `Send Messages` و `Attach Files`
- افتح رابط الدعوة الناتج وأضف البوت إلى سيرفرك.

## ملاحظات مهمة
- هذا إصدار أولي يعتمد على ClashKing API، وهي خدمة مجتمعية غير رسمية. قد تتغير الاستجابة أو لا تتوفر بيانات تاريخية لكل لاعب/يوم.
- الصورة المرجعية تبدو سجل Legend League يوميًا؛ لهذا لا يمكن ضمان إظهار نفس عدد السجلات أو نفس الإجماليات إذا لم يوفر المصدر تلك البيانات.
- ترتيب الألوان والشبكة مستوحى من المرجع وليس نسخة بكسل-بكسل. شعارات اللعبة والأيقونات مرسومة بشكل تقريبي.
- إذا ظهر خطأ API، راجع رسالة الخطأ في Discord. قد يحتاج مسار اليوم إلى تعديل حسب صيغة البيانات التي ترجعها الخدمة.
