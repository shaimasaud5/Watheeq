import re
import os
from groq import Groq


def clean_arabic_text(text: str) -> str:
    text = text.strip()
    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        line = re.sub(r"[ \t]+", " ", line)
        line = re.sub(r"(.)\1{2,}", r"\1\1", line)
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


class LLMCleaner:
    """
    Uses Groq to lightly correct Arabic-English mixed transcript turns.
    """

    PROMPT_TEMPLATE =  """

        You are a conservative transcript cleaner for Arabic-English mixed meetings.

        Task:
        Clean ONE speaker turn by fixing only obvious transcription errors.

        Important:
        - Do NOT translate.
        - Do NOT rewrite.
        - Do NOT explain.
        - Do NOT add alternatives.
        - Do NOT add or remove information.
        - Do NOT infer missing meaning.
        - If the text is understandable, keep it as close as possible to the original.
        - If a word is unclear or noisy, keep it unchanged.

        Output rules:
        1. Return ONLY the cleaned text.
        2. Keep the output as one line.
        3. Do NOT add speaker labels.
        4. Do NOT add arrows, notes, brackets, or explanations.
        5. Preserve the original meaning, tone, and order exactly.

        Preservation rules:
        6. Do NOT remove unclear, noisy, or partially recognized words.
        7. Do NOT replace unclear words with guessed words.
        8. Keep unclear words exactly as spoken because later stages may understand them from context.
        9. It is better to keep a noisy word than to replace it with a wrong technical term.

        Correction rules:
        10. Fix only clear spelling or transcription mistakes.
        11. Keep Arabic in Arabic.
        12. Keep English technical terms in English if they already appear.
        13. Convert Arabic-written technical terms to English ONLY when the full term is clearly spoken as a technical term.
        14. Do NOT convert normal Arabic words into technical terms because they sound similar.
        15. If unsure, keep the original wording unchanged.

        Technical terms:
        - ويب هوك / ويبوك / الويبوك -> webhook
        - ميتنق لينك / ميتينغ لينك -> meeting link
        - ترانسكريبت / الترانسكريبت -> transcript
        - تشنك / تشنكس -> chunk / chunks
        - امبيدنغز -> embeddings
        - اكستراكشن -> extraction
        - جنريشن    ->  generation

        Project document terms:
        - بي آر دي / بي ار دي -> BRD
        - ام او ام / إم أو إم -> MOM
        - اس ار اس /إس أر أس  -> SRS

        Final safety rule:
        When there is a conflict between correcting and preserving, choose preserving.

        Text:
        {text}
        
        """.strip()

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.model = model
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def _post_clean(self, text: str) -> str:
        text = text.strip()

        # Remove unwanted speaker labels if the model adds them
        text = re.sub(
            r"^(Speaker\s*\d*|Speaker\d+|المتحدث\s*\d*)\s*[:：-]\s*",
            "",
            text,
            flags=re.IGNORECASE
        )

        # Remove accidental quotes
        text = text.strip("\"'“”‘’")

        # Normalize spaces
        text = re.sub(r"[ \t]+", " ", text)

        return text.strip()

    def correct(self, text: str) -> str:
        if not text or not text.strip():
            return text

        cleaned_text = clean_arabic_text(text)
        prompt = self.PROMPT_TEMPLATE.format(text=cleaned_text)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
            )

            corrected = response.choices[0].message.content
            corrected = self._post_clean(corrected) if corrected else ""

            return corrected if corrected else cleaned_text

        except Exception as e:
            print("Groq error:", e)
            return cleaned_text