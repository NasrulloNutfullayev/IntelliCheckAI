# IntelliCheck AI Anti-Cheat Rejasi

Bu hujjat saytga chiqarish uchun emas. Bu o'qituvchi yoki loyiha egasi uchun texnik reja.

## Maqsad

Talabaning javobi:

- boshqa joydan copy-paste qilinganmi
- juda tez generatsiya qilinganmi
- AI yordamida yozilgan bo'lish ehtimoli bormi
- imtihon paytida sahifadan chiqib ketish yoki oynani almashtirish holatlari ko'pmi

shularni flag qilish.

## Muhim tamoyil

Anti-cheat tizim darhol avtomatik jazo bermasligi kerak. U faqat `risk score` va `flags` qaytarsin.
Yakuniy qaror o'qituvchida bo'lsin.

## Tavsiya etilgan arxitektura

### 1. Frontend signal qatlam

Talabaning brauzerida quyidagilar yig'iladi:

- `paste_attempt_count`: paste urinishlari soni
- `blur_count`: oynadan chiqib ketish soni
- `visibility_hidden_seconds`: tab yashiringan vaqt
- `typing_burst_score`: juda uzun javobning juda qisqa vaqtda paydo bo'lishi
- `delete_ratio`: matn tez yozilib keyin katta bloklar bilan o'chirilganmi
- `input_event_count`: haqiqiy typing event soni

Bu signal javob bilan birga backendga yuboriladi.

### 2. Backend risk engine

Backend quyidagi qoidalar bilan risk hisoblaydi:

- juda kam `input_event_count`, lekin juda uzun javob bo'lsa
- `blur_count` yoki `visibility_hidden_seconds` me'yordan katta bo'lsa
- vaqtga nisbatan matn hajmi g'ayritabiiy tez oshsa
- bir nechta student javoblari orasida semantic similarity juda yuqori bo'lsa
- student javobi bilan ommaviy LLM uslubiga xos patternlar topilsa

Natija:

```json
{
  "risk_score": 0.82,
  "flags": [
    "high_paste_risk",
    "tab_switching",
    "llm_style_pattern"
  ]
}
```

### 3. Modelga asoslangan AI-cheat tahlili

Ikki bosqich tavsiya qilinadi:

- Rule-based layer: tezkor va tushunarli flaglar
- ML layer: alohida classifier

Classifier uchun feature lar:

- o'rtacha gap uzunligi
- bir xil formatdagi bog'lovchi iboralar soni
- lexical diversity
- punctuation entropy
- question-answer semantic alignment
- typing behavior feature lari
- studentning oldingi yozuvlari bilan uslubiy masofa

## Tavsiya etilgan model yo'nalishlari

### Variant A: Gradient Boosting / XGBoost

Feature-engineered anti-cheat uchun amaliy va tushunarli variant.

Afzalligi:

- explainability kuchli
- kichik dataset bilan ham ishlaydi
- teacherga qaysi sabablar bilan flag bo'lganini ko'rsatish oson

### Variant B: RoBERTa yoki DeBERTa classifier

Matnning AI-generated ehtimolini topish uchun yaxshi.

Afzalligi:

- semantic signal kuchli
- keyin fine-tune qilinsa aniqligi oshadi

Kamchiligi:

- dataset kerak
- inference xarajati yuqoriroq

## Minimum viable anti-cheat

Birinchi bosqich uchun quyidagini tavsiya qilaman:

1. Paste block + paste urinishlarini log qilish
2. Blur/tab switch monitoring
3. Typing cadence va input event statistikasi
4. Javoblar orasida semantic similarity tekshiruvi
5. Teacher dashboardda faqat `flagged submission` ro'yxati

## Dataset kerak bo'lsa

Kelajakda real classifier uchun ikki xil label to'plash kerak:

- `human_written`
- `ai_assisted_or_suspicious`

Har submission uchun quyidagilar saqlanadi:

- javob matni
- typing telemetry
- imtihon vaqti
- group, subject, question
- teacher review label

## Tavsiya

Loyihaga birdan full auto AI-detector qo'shishdan ko'ra:

1. avval telemetry + rule-based risk engine
2. keyin teacher review loglari
3. undan keyin classifier training

shu ketma-ketlik eng xavfsiz va amaliy yo'l bo'ladi.
