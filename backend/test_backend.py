import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.data_loader import data_loader
from app.engine.rule_engine import rule_engine
from app.engine.graph_engine import graph_engine
from app.engine.recommender import course_recommender
from app.services.student_service import student_service
from app.services.chatbot_service import chatbot_service

def test_all():
    print("==================================================")
    print("🚀 BẮT ĐẦU TEST TOÀN DIỆN BACKEND FASTAPI ENGINE")
    print("==================================================")

    # 1. Test DataLoader
    courses = data_loader.get_all_courses()
    rules = data_loader.get_all_rules()
    profile = data_loader.get_student_profile()
    print(f"1. [DataLoader] Môn học: {len(courses)}, Quy tắc: {len(rules)}, SV: {profile.get('info', {}).get('student_name')}")
    assert len(courses) > 0, "Không có môn học nào!"
    assert len(rules) > 0, "Không có quy tắc nào!"

    # 2. Test Rule Engine: Đồ án 1 và 2 cùng lúc
    print("\n2. [RuleEngine] Test kiểm tra Đồ án 1 (ET3290) và Đồ án 2 (ET4010)...")
    check_da2 = rule_engine.check_eligibility("ET4010", concurrent_codes=["ET3290"])
    print(f"   -> ET4010: is_eligible={check_da2['is_eligible']}, status={check_da2['status']}")
    assert check_da2["is_eligible"] == True, "ET4010 phải đủ điều kiện đăng ký!"

    check_da1 = rule_engine.check_eligibility("ET3290")
    print(f"   -> ET3290: is_eligible={check_da1['is_eligible']}, status={check_da1['status']}")
    print(f"   -> Lý do ET3290: {check_da1['reasons']}")

    # 3. Test Graph Engine: Mô phỏng trượt môn
    print("\n3. [GraphEngine] Mô phỏng trượt môn ET2040 (Cấu kiện điện tử)...")
    sim = graph_engine.get_impact_analysis("ET2040")
    print(f"   -> Mức độ ảnh hưởng: {sim['severity']}")
    print(f"   -> Số môn bị chặn trực tiếp: {len(sim['direct_blocked_courses'])} môn ({', '.join(d['code'] for d in sim['direct_blocked_courses'])})")
    print(f"   -> Tổng số môn bị ảnh hưởng chuỗi: {sim['total_blocked']} môn")
    assert sim["total_blocked"] > 0, "Trượt ET2040 phải ảnh hưởng chuỗi môn sau!"

    # 4. Test Degree Audit
    print("\n4. [StudentService] Báo cáo Degree Audit...")
    audit = student_service.audit_degree()
    print(f"   -> CPA: {audit['cpa']}")
    print(f"   -> Tín chỉ tích lũy: {audit['total_credits_accumulated']:.1f} / {audit['total_credits_required']} TC")
    print(f"   -> Tỷ lệ hoàn thành: {audit['completion_percentage']}%")
    print(f"   -> Môn bắt buộc còn thiếu: {len(audit['unlearned_compulsory_courses'])} môn")

    # 5. Test Recommender
    print("\n5. [Recommender] Gợi ý môn kỳ tới theo hướng Thiết kế Vi mạch (IC_DESIGN)...")
    rec = course_recommender.recommend(target_track="IC_DESIGN", max_credits=20)
    print(f"   -> Tổng tín chỉ đề xuất: {rec['total_credits_suggested']} TC")
    for idx, c in enumerate(rec["recommended_courses"], 1):
        print(f"      {idx}. {c['code']} - {c['name']} ({c['credits']} TC) [{c['category']}]")
    assert len(rec["recommended_courses"]) > 0, "Phải đề xuất được ít nhất 1 môn!"

    # 6. Test Chatbot Service
    print("\n6. [ChatbotService] Thử nghiệm hỏi đáp ngôn ngữ tự nhiên...")
    q1 = "Kỳ này mình học đồ án 1 và 2 cùng lúc được không bạn?"
    a1 = chatbot_service.process_message(q1)
    print(f"   Q: {q1}")
    print(f"   A:\n{a1['reply'][:250]}...\n")
    assert "ĐƯỢC PHÉP" in a1["reply"], "Chatbot phải xác nhận ĐATK 1 và 2 học được cùng lúc!"

    q2 = "Mình muốn theo hướng Thiết kế Vi mạch thì kỳ tới nên chọn những môn nào?"
    a2 = chatbot_service.process_message(q2)
    print(f"   Q: {q2}")
    print(f"   A:\n{a2['reply'][:250]}...\n")
    assert len(a2["data_context"]["recommended_courses"]) > 0, "Chatbot phải gợi ý môn vi mạch!"

    print("\n==================================================")
    print("🎉 TẤT CẢ 6 BỘ TEST ĐÃ CHẠY THÀNH CÔNG 100%!")
    print("==================================================")

if __name__ == "__main__":
    test_all()
