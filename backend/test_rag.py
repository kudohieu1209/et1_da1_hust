import sys
import os

# Đảm bảo đường dẫn backend nằm trong sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.rag.document_loader import document_loader
from app.rag.vector_store import vector_store
from app.rag.rag_engine import rag_engine
from app.services.chatbot_service import chatbot_service

def test_rag_pipeline():
    print("=" * 60)
    print("🚀 BẮT ĐẦU KIỂM THỬ TOÀN DIỆN RAG & HYBRID AGENT CHO HUST")
    print("=" * 60)

    # 1. Kiểm tra DocumentLoader
    print("\n1. [DocumentLoader] Đọc tài liệu quy chế HUST...")
    files = document_loader.get_document_files()
    print(f"   -> Tìm thấy {len(files)} files: {[f.name for f in files]}")
    assert len(files) >= 3, "Phải có tối thiểu 3 tài liệu quy chế HUST!"

    chunks = document_loader.load_all_chunks()
    print(f"   -> Tổng số chunks tạo ra: {len(chunks)}")
    assert len(chunks) > 0, "Không được để danh sách chunks rỗng!"

    # 2. Kiểm tra VectorStoreManager & ChromaDB Sync
    print("\n2. [VectorStore] Đồng bộ dữ liệu vào ChromaDB...")
    sync_res = vector_store.sync_documents(force=True)
    print(f"   -> Kết quả đồng bộ: {sync_res['status']}, tổng chunks: {sync_res['total_chunks']}")
    assert sync_res["total_chunks"] > 0, "ChromaDB phải chứa các vector chunks!"

    # 3. Kiểm tra Similarity Search (Retriever)
    print("\n3. [Retriever] Kiểm tra tìm kiếm tương đồng vector...")
    
    # Query 1: Học bổng
    q1 = "Tiêu chuẩn xét học bổng khuyến khích học tập loại Xuất sắc"
    res1 = vector_store.similarity_search(q1, k=2)
    print(f"   Query: '{q1}'")
    assert len(res1) > 0, "Không tìm thấy kết quả cho q1"
    print(f"   -> Top 1 match: [{res1[0]['metadata'].get('source')}] {res1[0]['text'][:120]}...")
    assert "học bổng" in res1[0]["text"].lower(), "Tài liệu trích xuất phải chứa thông tin học bổng!"

    # Query 2: Cảnh cáo học tập
    q2 = "Sinh viên bị cảnh cáo học tập mức 2 được đăng ký tối đa bao nhiêu tín chỉ?"
    res2 = vector_store.similarity_search(q2, k=2)
    print(f"\n   Query: '{q2}'")
    assert len(res2) > 0, "Không tìm thấy kết quả cho q2"
    print(f"   -> Top 1 match: [{res2[0]['metadata'].get('source')}] {res2[0]['text'][:120]}...")
    assert "14" in res2[0]["text"] or "cảnh cáo" in res2[0]["text"].lower(), "Tài liệu phải chứa quy định cảnh cáo mức 2!"

    # 4. Kiểm tra Hybrid Chatbot Router
    print("\n4. [Hybrid Agent] Kiểm tra điều hướng Intent...")

    # Test case A: Hỏi Quy chế HUST -> Router kích hoạt RAG
    msg_rag = "Điều kiện để nhận Đồ án tốt nghiệp Cử nhân tại Bách Khoa là gì?"
    ans_rag = chatbot_service.process_message(msg_rag)
    print(f"\n   Q (RAG): {msg_rag}")
    print(f"   -> Intent: {ans_rag['intent']}")
    print(f"   -> Model/Engine: {ans_rag.get('model_used')}")
    print(f"   -> Sources: {ans_rag.get('sources')}")
    print(f"   -> Reply preview: {ans_rag['reply'][:200]}...")
    assert ans_rag["intent"] == "RAG_HUST_KNOWLEDGE", "Phải kích hoạt RAG cho câu hỏi quy chế ĐATN!"
    assert len(ans_rag.get("sources", [])) > 0, "Phải có nguồn trích dẫn tài liệu HUST!"

    # Test case B: Hỏi Học bổng -> Router kích hoạt RAG
    msg_sch = "Sinh viên cần đạt điều kiện gì để được học bổng loại A?"
    ans_sch = chatbot_service.process_message(msg_sch)
    print(f"\n   Q (RAG): {msg_sch}")
    print(f"   -> Intent: {ans_sch['intent']}")
    print(f"   -> Sources: {ans_sch.get('sources')}")
    assert ans_sch["intent"] == "RAG_HUST_KNOWLEDGE"

    # Test case C: Hỏi Logic môn học (ĐATK 1 & 2) -> Deterministic Engine
    msg_course = "Kỳ này mình học đồ án 1 và đồ án 2 cùng lúc được không?"
    ans_course = chatbot_service.process_message(msg_course)
    print(f"\n   Q (Deterministic): {msg_course}")
    print(f"   -> Intent: {ans_course['intent']}")
    print(f"   -> Reply: {ans_course['reply'][:150]}...")
    assert ans_course["intent"] == "COURSE_ELIGIBILITY_CHECK", "Phải dùng logic kiểm tra môn học!"

    # Test case D: Hỏi gợi ý môn theo hướng Vi mạch -> Recommender Engine
    msg_rec = "Mình muốn theo hướng Thiết kế Vi mạch thì kỳ tới nên chọn những môn nào?"
    ans_rec = chatbot_service.process_message(msg_rec)
    print(f"\n   Q (Recommender): {msg_rec}")
    print(f"   -> Intent: {ans_rec['intent']}")
    print(f"   -> Track: {ans_rec['data_context']['track_name']}")
    assert ans_rec["intent"] == "COURSE_RECOMMENDATION", "Phải nhận diện intent gợi ý môn vi mạch!"

    print("\n" + "=" * 60)
    print("✅ TẤT CẢ CÁC BÀI TEST RAG & HYBRID AGENT ĐỀU ĐẠT CHUẨN XUẤT SẮC!")
    print("=" * 60)

if __name__ == "__main__":
    test_rag_pipeline()
