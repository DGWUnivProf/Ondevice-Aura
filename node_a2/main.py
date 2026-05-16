import threading
import time
import sys
import grpc
from concurrent import futures
import aura_pb2_grpc
from config import Config
from audio_processor import record_vad, run_stt, speak_text
from emotion_analyzer import analyze_voice_emotion
from network_manager import NetworkManager

def main():
    # 1. 네트워크 매니저 초기화 (TTS 콜백 연결)
    net_manager = NetworkManager(tts_callback=speak_text)
    
    # 2. gRPC 서버 초기화 및 시작
    # (종료 시 제어를 위해 start_grpc_server 함수 대신 메인에서 직접 서버 객체 관리)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    aura_pb2_grpc.add_AuraTTSServicer_to_server(net_manager, server)
    server.add_insecure_port(f"[::]:{Config.MY_TTS_SERVER_PORT}")
    
    server.start()
    print(f"📡 TTS 리스너 가동 성공 (Port: {Config.MY_TTS_SERVER_PORT})")
    print("✨ 모든 모듈 로드 완료. 시스템 시작. (종료하려면 Ctrl+C)")

    # 💡 전체 루프를 try-except로 감싸 Ctrl+C 발생 시 무조건 finally로 가게 합니다.
    try:
        while True:
            # 3. 음성 감지 및 녹음
            if record_vad():
                # 4. 텍스트 변환 (STT)
                text = run_stt()
                if not text or len(text.strip()) < 2: 
                    continue
                
                # 5. 감정 분석
                v, a, conf = analyze_voice_emotion(Config.RECORD_FILE)
                print(f"📝 인식: {text} | 📊 VA: {v:.2f}, {a:.2f}")

                # 6. 표정 노드로 데이터 전송
                try:
                    net_manager.send_to_face(text, v, a, conf)
                    print("✅ 전송 완료")
                except Exception as net_err:
                    print(f"⚠️ 표정 노드 전송 실패 (상대 노드가 꺼져있을 수 있음): {net_err}")

    except KeyboardInterrupt:
        print("\n👋 Ctrl+C 신호 감지: 안전하게 프로세스를 종료합니다...")
        
    except Exception as e:
        print(f"\n❌ 치명적 오류 발생: {e}")
        
    finally:
        # 💡 [핵심] 종료 시 자원을 깨끗하게 해제하는 청소부 역할
        print("🧹 리소스 정리 중...")
        
        # 1. gRPC 서버 안전하게 정지 (0초 대기 후 즉시 정지)
        try:
            server.stop(0)
            print("🔒 gRPC 수신 서버가 안전하게 중지되었습니다.")
        except Exception as e:
            print(f"⚠️ 서버 중지 중 에러: {e}")
            
        print("✅ 시스템이 성공적으로 종료되었습니다. 터미널 제어권을 반환합니다.")
        sys.exit(0)

if __name__ == "__main__":
    main()