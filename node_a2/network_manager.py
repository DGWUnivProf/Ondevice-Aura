import grpc
import threading
from concurrent import futures
import aura_pb2
import aura_pb2_grpc
from config import Config

class NetworkManager(aura_pb2_grpc.AuraTTSServicer):
    def __init__(self, tts_callback):
        self.tts_callback = tts_callback
        self.channel = grpc.insecure_channel(Config.FACE_NODE_TARGET)
        self.perception_stub = aura_pb2_grpc.AuraPerceptionStub(self.channel)
        
        # 💡 TTS 중복 출력 방지를 위한 플래그 및 락(Lock) 추가
        self.is_speaking = False
        self.speaking_lock = threading.Lock()

    # Node B로부터 답변 수신 (Server 역할)
    def SendDialogue(self, request, context):
        # 💡 스레드 안전하게 현재 말하는 중인지 체크
        with self.speaking_lock:
            if self.is_speaking:
                print(f"⚠️ [무시] 현재 TTS 출력 중입니다. 새로 수신된 요청을 드롭합니다: '{request.text}'")
                # 무시하더라도 gRPC 프로토콜 규격을 맞춰서 정상 응답을 보냅니다.
                return aura_pb2.EmpathyResponse(error_code=aura_pb2.ErrorCode.NONE)
            
            # 말하는 중이 아니라면 점유 상태로 변경
            self.is_speaking = True

        print(f"\n📩 [수신] Node B 답변: {request.text}")
        
        # 실제 TTS 출력을 수행하고 상태를 해제하는 래퍼 함수 실행
        threading.Thread(target=self._tts_worker, args=(request.text,), daemon=True).start()
        
        return aura_pb2.EmpathyResponse(error_code=aura_pb2.ErrorCode.NONE)

    def _tts_worker(self, text):
        """실제 TTS를 실행하고 종료 시 플래그를 해제하는 워커 함수"""
        try:
            # 외부에서 전달받은 오디오 프로세서의 speak_text 실행 (동기식 재생 완료까지 대기)
            self.tts_callback(text)
        finally:
            # 재생이 끝나면 에러가 나더라도 확실하게 플래그를 거짓(False)으로 돌려놓음
            with self.speaking_lock:
                self.is_speaking = False
                print("🔄 TTS 출력 완료: 새로운 입력을 받을 준비가 되었습니다.")

    def send_to_face(self, text, v, a, conf):
        candidate = aura_pb2.EmotionCandidate(
            source="voice", valence=v, arousal=a, confidence=conf, text=text
        )
        return self.perception_stub.SendVoicePerception(candidate)

def start_grpc_server(manager):
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
        aura_pb2_grpc.add_AuraTTSServicer_to_server(manager, server)
        
        port = Config.MY_TTS_SERVER_PORT
        server.add_insecure_port(f"[::]:{port}")
        server.start()
        
        print(f"📡 TTS 리스너 가동 성공 (Port: {port})")
        server.wait_for_termination()
    except Exception as e:
        print(f"❌ gRPC 서버 시작 실패: {e}")