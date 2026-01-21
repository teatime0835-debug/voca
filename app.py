import streamlit as st
import base64
import json
import random
from openai import OpenAI

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="이미지 영단어 테스트", layout="wide")
st.title("📸 이미지로 영단어 테스트 만들기")

client = OpenAI()

# =====================
# 유틸
# =====================
def image_to_base64(file):
    return base64.b64encode(file.read()).decode()

# =====================
# 세션 초기화
# =====================
for key in ["words", "quiz", "user_answers", "submitted"]:
    if key not in st.session_state:
        st.session_state[key] = None

# =====================
# 1️⃣ 이미지 업로드
# =====================
uploaded = st.file_uploader("영단어가 포함된 이미지를 업로드하세요", type=["png", "jpg", "jpeg"])

if uploaded:
    st.image(uploaded, width=350)
    img64 = image_to_base64(uploaded)

    if st.button("🔍 이미지에서 영단어 추출"):
        with st.spinner("영단어 인식 중..."):
            prompt = """
            이미지 속에 포함된 영단어를 모두 추출하라.

            조건:
            - 소문자
            - 중복 제거
            - 영어 단어만

            JSON 형식:
            { "words": ["word1", "word2"] }
            """

            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img64}"}}
                    ]
                }],
                response_format={"type": "json_object"}
            )

            st.session_state.words = json.loads(res.choices[0].message.content)["words"]

# =====================
# 2️⃣ 단어 수정 / 추가
# =====================
if st.session_state.words:
    st.subheader("✏️ 인식된 영단어")

    edited = []
    for i, w in enumerate(st.session_state.words):
        edited.append(st.text_input(f"단어 {i+1}", w))

    st.markdown("➕ 단어 추가 (최대 2개)")
    edited.append(st.text_input("추가 1"))
    edited.append(st.text_input("추가 2"))

    final_words = list(dict.fromkeys([w.strip().lower() for w in edited if w.strip()]))
    st.info(f"최종 단어 수: {len(final_words)}개")

    # =====================
    # 3️⃣ 문제 생성
    # =====================
    if st.button("📝 테스트 생성"):
        with st.spinner("문항 생성 중..."):
            total_q = len(final_words) + 2

            # 🔹 유형 비율 강제
            types = ["A", "B", "C", "D", "E"]
            base = total_q // 5
            remainder = total_q % 5

            type_plan = {t: base for t in types}
            for t in types[:remainder]:
                type_plan[t] += 1

            quiz = []
            for t, cnt in type_plan.items():
                if cnt == 0:
                    continue

                type_prompt = f"""
                너는 중학교 영어 교사다.
                다음 유형 {t} 문제를 {cnt}개 만들어라.
                단어 목록: {final_words}

                문제 유형 지시 (형식을 반드시 따를 것):

                A. (객관식)
                예: 다음 중 'local'의 뜻으로 알맞은 것은?

                B. (객관식, 예문에서 해당 영단어에 밑줄이 그어져 있음)
                예: 다음 예문에서 'succeed'의 의미로 가장 적절한 것은?
                The team didn't succeed in winning the game.

                C. (객관식, 빈칸)
                예: 다음 빈칸에 들어갈 영단어로 알맞은 것은?
                She is very ______ to go on that trip.

                D. (단답형)
                예: '상태'라는 뜻을 갖고 's'로 시작하는 영단어를 입력하시오.

                E. (단답형, 빈칸)
                예: 다음 빈칸에 들어갈 알맞은 영단어를 입력하시오.
                The car drives in a __________ path.

                반드시 JSON 형식:
                {{
                  "questions": [
                    {{
                      "type": "{t}",
                      "question": "...",
                      "choices": ["a","b","c","d"] or null,
                      "answer": ["정답"] or "정답",
                      "explanation": "풀이"
                    }}
                  ]
                }}
                """

                r = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": type_prompt}],
                    response_format={"type": "json_object"}
                )

                quiz.extend(json.loads(r.choices[0].message.content)["questions"])

            random.shuffle(quiz)

            st.session_state.quiz = quiz
            st.session_state.user_answers = {}
            st.session_state.submitted = False

# =====================
# 4️⃣ 문제 풀이
# =====================
if st.session_state.quiz:
    st.subheader("🧪 영단어 테스트")

    # ✅ 완료 버튼을 먼저 처리
    if st.button("✅ 완료"):
        st.session_state.submitted = True

        score = 0
        for i, q in enumerate(st.session_state.quiz):
            u = st.session_state.user_answers.get(i, "")
            a = q["answer"]

            if isinstance(a, list) and u in a:
                score += 1
            elif isinstance(a, str) and u.strip().lower() == a.lower():
                score += 1

        st.session_state.score = score

    # 🔽 그 다음에 문제 출력
    for i, q in enumerate(st.session_state.quiz):
        st.markdown(f"### {i+1}. 문제")
        st.write(q["question"])

        if q["choices"]:
            ans = st.radio(
                "선택하세요",
                q["choices"],
                key=f"q_{i}"
            )
        else:
            ans = st.text_input("답을 입력하세요", key=f"q_{i}")

        st.session_state.user_answers[i] = ans

        if st.session_state.submitted:
            correct = q["answer"]
            is_correct = (
                ans in correct if isinstance(correct, list)
                else ans.strip().lower() == correct.lower()
            )

            st.markdown(
                f"**정답:** {correct}  \n"
                f"**풀이:** {q['explanation']}  \n"
                f"{'✅ 정답' if is_correct else '❌ 오답'}"
            )

    if st.session_state.submitted:
        st.success(
            f"🎉 점수: {st.session_state.score} / {len(st.session_state.quiz)}"
        )
