import json
import requests
import sys
import os

# 경로 추가 (src 폴더를 참조하기 위함)
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from domain.knowledge.node_c import KnowledgeRepository

# [설정]
MODEL_NAME = "aura-gemma:latest"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PW = "password123"

class AuraSystem:
    def __init__(self):
        self.repo = KnowledgeRepository(NEO4J_URI, NEO4J_USER, NEO4J_PW)
        print(f"✅ Node C (Neo4j) 연결 완료")
        print(f"✅ Node B (Ollama: {MODEL_NAME}) 준비 완료")

    def generate_response(self, scenario, keyword):
        # 1. Neo4j에서 지식 추출
        knowledge = self.repo.get_emotional_context(keyword)
        knowledge_str = "\n".join(knowledge) if knowledge else "관련 상식 없음"

        # 2. 프롬프트 구성 (대화형 상담 스타일)
        prompt = f"""
        당신은 공감 능력이 뛰어난 AI 상담사 '아우라(Aura)'입니다.
        아래 지식을 참고하여 사용자의 마음을 어루만져 주세요.
        
        [지침]:
        - 반드시 한국어로만 답변하세요.
        - 답변은 2~3문장 내외로 짧고 간결하게 하세요.
        - 혼자 결론을 내리지 말고, 사용자의 기분을 물어보거나 대화를 이어갈 수 있는 질문을 던지세요.
        - 진정성 있는 상담사 말투를 유지하세요.

        [참고 지식]:
        {knowledge_str}

        [사용자 상황]: {scenario}

        [아우라의 답변]:"""

        # 3. Ollama API 호출 (GPU 사용)
        try:
            res = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": MODEL_NAME, 
                    "prompt": prompt, 
                    "stream": False,
                    "options": {"num_gpu": 1} # 1개의 레이어만 GPU 사용 (안정성 테스트)
                },
                timeout=120 # GPU 사용 시에는 2분이면 충분합니다.
            )
            data = res.json()
            if "response" in data:
                return data["response"]
            else:
                return f"실패 (Ollama 응답): {json.dumps(data)}"
        except Exception as e:
            return f"에러 발생: {e}"

# [테스트 시나리오]
test_cases = [
    ("최선을 다했던 프로젝트가 결국 실패로 끝났어. 너무 허탈해.", "failure"),
    ("오랫동안 키우던 강아지가 하늘나라로 갔어. 너무 힘들어.", "dog"),
    ("새로운 환경에 왔는데 나만 혼자인 것 같아. 아무도 말을 안 걸어줘.", "lonely")
]

if __name__ == "__main__":
    aura = AuraSystem()
    
    print("\n" + "="*50)
    print("🌟 아우라(Aura) 대화형 상담 테스트 시작 (GPU 가속)")
    print("="*50)

    for i, (scenario, kw) in enumerate(test_cases):
        print(f"\n📍 [Test #{i+1}] 상황: {scenario}")
        response = aura.generate_response(scenario, kw)
        print(f"💬 아우라: {response}")
        print("-" * 30)

    aura.repo.close()
    print("\n✅ 모든 테스트가 완료되었습니다.")
