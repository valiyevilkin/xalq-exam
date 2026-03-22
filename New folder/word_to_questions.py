#!/usr/bin/env python3
"""
Word Sual Faylını HTML QUESTIONS Array-ə Çevirən Script
========================================================

WORD FAYLINDA SUAL FORMATI:
────────────────────────────

TİP 1 — Tək düzgün cavablı çoxseçimli:
  1. Sual mətni?
  A) Seçim 1
  B) Seçim 2
  C) Seçim 3
  D) Seçim 4
  Düzgün cavab: B

TİP 2 — Birdən çox düzgün cavablı:
  2. Sual mətni?
  A) Seçim 1
  B) Seçim 2
  C) Seçim 3
  D) Seçim 4
  Düzgün cavab: A, C

TİP 3 — Doğru/Yanlış:
  3. Sual mətni.
  Düzgün cavab: Doğru
  (və ya: Düzgün cavab: Yanlış)
  NOT: Seçimlər avtomatik ["Doğru", "Yanlış"] olacaq

TİP 4 — Mətn cavabı (rəqəm/söz):
  4. Sual mətni?
  Cavab: 542
  (və ya: Cavab: Bəli)

İZAHAT (istəyə bağlı, hər növ sual üçün):
  Explanation: İzahat mətni bura yazılır

QEYD:
- Sualların sırası önəmli deyil
- Boş sətrlər nəzərə alınmır
- Sual nömrəsi olmaya da bilər (sadəcə "Sual mətni?" kimi)
- "Düzgün cavab:" əvəzinə "Doğru cavab:" da qəbul edilir
"""

import re
import sys
import json
from pathlib import Path

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


def read_input_file(filepath: str) -> list[str]:
    """Faylı oxuyur: .docx və ya .txt/.md dəstəklənir."""
    path = Path(filepath)
    if not path.exists():
        print(f"XƏTA: Fayl tapılmadı: {filepath}")
        sys.exit(1)

    if path.suffix.lower() == '.docx':
        if not DOCX_AVAILABLE:
            print("XƏTA: python-docx qurulu deyil. Qurmaq üçün: pip install python-docx")
            sys.exit(1)
        doc = DocxDocument(filepath)
        lines = [para.text for para in doc.paragraphs]
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()

    return lines


def normalize(text: str) -> str:
    """Mətni normallaşdırır: boşluqları azaldır, başını/sonunu kəsir."""
    return re.sub(r'\s+', ' ', text).strip()


def parse_questions(lines: list[str]) -> list[dict]:
    """Sətirləri oxuyub sual siyahısını qaytarır."""
    questions = []

    # Boş sətirləri filtr et, normallaşdır
    lines = [normalize(l) for l in lines if normalize(l)]

    i = 0
    while i < len(lines):
        line = lines[i]

        # Sual sətrini tap: rəqəmlə başlayan ("1. ...") və ya sual işarəsi ilə bitən
        q_match = re.match(r'^(?:\d+[\.\)]\s*)?(.+)$', line)
        if not q_match:
            i += 1
            continue

        potential_q = q_match.group(1).strip()

        # Növbəti sətrlər seçimmi, cavab göstəricimidir, yoxsa?
        opts = []
        correct_raw = None
        explanation = None
        text_answer = None
        j = i + 1

        while j < len(lines):
            next_line = lines[j]

            # Seçim sətri: A) ... / A. ... / a) ...
            opt_match = re.match(r'^([A-Ea-e])[\.\)]\s*(.+)$', next_line)

            # Cavab sətri: "Düzgün cavab:", "Doğru cavab:", "Correct:"
            ans_match = re.match(
                r'^(?:Düzgün cavab|Doğru cavab|Correct answer|Answer)\s*:\s*(.+)$',
                next_line, re.IGNORECASE
            )

            # Mətn cavabı: "Cavab:", "Answer:"
            text_ans_match = re.match(
                r'^(?:Cavab|Mətn cavabı|Text answer)\s*:\s*(.+)$',
                next_line, re.IGNORECASE
            )

            # İzahat: "Explanation:", "İzahat:"
            expl_match = re.match(
                r'^(?:Explanation|İzahat|Açıqlama)\s*:\s*(.+)$',
                next_line, re.IGNORECASE
            )

            if opt_match:
                opts.append(opt_match.group(2).strip())
                j += 1
            elif ans_match:
                correct_raw = ans_match.group(1).strip()
                j += 1
            elif text_ans_match:
                text_answer = text_ans_match.group(1).strip()
                j += 1
            elif expl_match:
                explanation = expl_match.group(1).strip()
                j += 1
            else:
                # Yeni sual başlayır
                break

        # Sualı kateqoriyalandır
        if text_answer is not None:
            # TİP 4: Mətn cavabı
            q_obj = {
                "q": potential_q,
                "type": "text",
                "answer": text_answer
            }
            if explanation:
                q_obj["explanation"] = explanation
            questions.append(q_obj)
            i = j

        elif correct_raw is not None and not opts:
            # TİP 3: Doğru/Yanlış (seçimsiz)
            correct_lower = correct_raw.strip().lower()
            if correct_lower in ('doğru', 'düzgün', 'true', 'bəli', 'yes'):
                correct_idx = 0
            else:
                correct_idx = 1
            q_obj = {
                "q": potential_q,
                "opts": ["Doğru", "Yanlış"],
                "correct": correct_idx
            }
            if explanation:
                q_obj["explanation"] = explanation
            questions.append(q_obj)
            i = j

        elif opts and correct_raw is not None:
            # TİP 1 və ya TİP 2: Çoxseçimli
            # Cavabda vergül varsa → çoxlu düzgün cavab (TİP 2)
            if ',' in correct_raw:
                # TİP 2: Birdən çox cavab
                letters = [c.strip().upper() for c in correct_raw.split(',')]
                correct_indices = []
                for letter in letters:
                    idx = ord(letter) - ord('A')
                    if 0 <= idx < len(opts):
                        correct_indices.append(idx)
                q_obj = {
                    "q": potential_q,
                    "opts": opts,
                    "correct": correct_indices,
                    "multi": True
                }
            else:
                # TİP 1: Tək cavab
                letter = correct_raw.strip().upper()
                # Rəqəm də qəbul et: "1" → 0, "2" → 1 ...
                if letter.isdigit():
                    correct_idx = int(letter) - 1
                else:
                    correct_idx = ord(letter) - ord('A')
                    if correct_idx < 0 or correct_idx >= len(opts):
                        correct_idx = 0
                q_obj = {
                    "q": potential_q,
                    "opts": opts,
                    "correct": correct_idx
                }

            if explanation:
                q_obj["explanation"] = explanation
            questions.append(q_obj)
            i = j

        else:
            # Sual kimi görünmür, növbəti sətirə keç
            i += 1

    return questions


def format_js_array(questions: list[dict]) -> str:
    """Sual siyahısını JS kodu kimi formatla."""
    lines = ["const QUESTIONS = ["]

    for q in questions:
        lines.append("  {")
        # Sual mətni
        q_text = q['q'].replace('\\', '\\\\').replace('"', '\\"')
        lines.append(f'    q: "{q_text}",')

        # Tip
        q_type = q.get('type', 'single')

        if q_type == 'text':
            answer = str(q['answer']).replace('"', '\\"')
            lines.append(f'    type: "text",')
            lines.append(f'    answer: "{answer}",')
        else:
            opts_str = ', '.join(f'"{o.replace(chr(34), chr(92)+chr(34))}"' for o in q['opts'])
            lines.append(f'    opts: [{opts_str}],')

            if q.get('multi'):
                correct_str = json.dumps(q['correct'])
                lines.append(f'    correct: {correct_str},  // Çoxlu düzgün cavab')
                lines.append(f'    multi: true,')
            else:
                lines.append(f'    correct: {q["correct"]},')

        if 'explanation' in q:
            expl = q['explanation'].replace('"', '\\"')
            lines.append(f'    explanation: "{expl}",')

        lines.append("  },")

    lines.append("];")
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nİSTİFADƏ:")
        print("  python word_to_questions.py sorular.docx")
        print("  python word_to_questions.py sorular.txt")
        print("  python word_to_questions.py sorular.txt -o output.js")
        sys.exit(0)

    input_file = sys.argv[1]
    output_file = None

    if '-o' in sys.argv:
        idx = sys.argv.index('-o')
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]

    print(f"Fayl oxunur: {input_file}")
    lines = read_input_file(input_file)
    print(f"  {len(lines)} sətir tapıldı")

    questions = parse_questions(lines)
    print(f"  {len(questions)} sual emal edildi")

    # Statistika
    types = {"single": 0, "multi": 0, "bool": 0, "text": 0}
    for q in questions:
        if q.get('type') == 'text':
            types['text'] += 1
        elif q.get('multi'):
            types['multi'] += 1
        elif q.get('opts') == ['Doğru', 'Yanlış']:
            types['bool'] += 1
        else:
            types['single'] += 1

    print(f"\n  📊 Sual tipləri:")
    print(f"     Tək cavablı (Tip 1):      {types['single']}")
    print(f"     Çox cavablı (Tip 2):      {types['multi']}")
    print(f"     Doğru/Yanlış (Tip 3):     {types['bool']}")
    print(f"     Mətn cavabı (Tip 4):      {types['text']}")

    js_output = format_js_array(questions)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(js_output)
        print(f"\n✅ Nəticə yazıldı: {output_file}")
    else:
        print("\n" + "="*60)
        print("AŞAĞIDAKI KODU HTML FAYLINA YAPIŞDIRIN:")
        print("="*60 + "\n")
        print(js_output)
        print("\n" + "="*60)


if __name__ == '__main__':
    main()
