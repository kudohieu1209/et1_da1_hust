"""Check student service views and PDF confirmation with synthetic API data."""
import functools
import json
import threading
from http.server import ThreadingHTTPServer

from playwright.sync_api import sync_playwright
from check_auth_ui import QuietHandler, ROOT


def main():
    output = ROOT / 'tmp' / 'student-services-ui'
    output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'frontend/dist')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    account = {'student_id': '20221234', 'student_name': 'Sinh viên kiểm thử', 'class_name': 'Lớp thử - K67', 'program_code': 'ET1', 'auth_provider': 'ctt'}
    def section(records=None, **extra):
        return {'status': 'synced', 'synced_at': '2026-11-15T00:00:00Z', 'source_url': 'https://ctt-sis.hust.edu.vn/', 'records': records or [], 'tables': [], **extra}
    sections = {
        'english': section([{'score': 0, 'test_date': '2026-11-15', 'certificate_type': 'Bài thi tổng hợp', 'listening': 0, 'reading': 0}]),
        'tuition': section([{'semester': '2026.1', 'tuition_fee': 9850000, 'paid': None, 'debt': 0}]),
        'classmates': section([{'student_id': '20221235', 'student_name': 'Bạn cùng lớp kiểm thử', 'class_name': 'Lớp thử - K67'}], tables=[{'id':'fixture', 'headers':['MSSV','Họ tên'], 'rows':[['20221235','Bạn cùng lớp kiểm thử']]}]),
        'warning': section(warning_level=0),
        'certificates': section(requirements={'220': 'completed', '230': 'incomplete', '240': 'unverified'}),
        'timetable': section([{'id': 'fixture', 'course_code': 'ET2030', 'course_name': 'Lập trình', 'class_code': '123456', 'day_of_week': 8, 'start_period': 1, 'end_period': 3, 'room': 'D3-201', 'weeks': '1-16'}]),
        'temporary_timetable': section(status='empty'),
        'exams': section(status='unavailable', message='Chưa thấy trang lịch thi trong CTT. Có thể nhập PDF.'),
    }
    preview = [
        {'course_code': 'ET2030', 'course_name': 'Lập trình', 'class_code': '123456', 'exam_date': '2026-12-15', 'exam_time': '07:30', 'room': 'D3-201', 'exam_type': '', 'notes': ''},
        {'course_code': 'ET2050', 'course_name': 'Lý thuyết mạch', 'class_code': '999999', 'exam_date': '2026-12-16', 'exam_time': '09:30', 'room': 'D5-201', 'exam_type': '', 'notes': ''},
    ]
    saved = []
    errors = []
    def api(route):
        path = route.request.url.split('/api/', 1)[1]
        data = {}
        if path == 'auth/me': data = account
        elif path == 'student/profile': data = {'info': account, 'transcript': [{'code': 'ET2030', 'credits': 3, 'letter_grade': 'B', 'is_passed': True}], 'school_sync': {'synced_at': 'fixture'}}
        elif path == 'student/audit': data = {'student_info': account, 'cpa': 3, 'total_credits_required': 126, 'total_credits_accumulated': 3}
        elif path == 'student/school-services': data = {'sections': sections}
        elif path == 'conversations': data = {'conversations': []}
        elif path == 'student/exams/preview': data = {'records': preview}
        elif path == 'student/exams/import':
            payload = route.request.post_data_json
            saved.append(payload)
            sections['exams'] = section(payload['exams'], source_type='imported_pdf')
            data = {'status': 'success', 'total': len(payload['exams'])}
        route.fulfill(content_type='application/json', body=json.dumps(data))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chromium', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('**/api/**', api)
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.get_by_role('button', name='Tiện ích CTT (Học phí, TOEIC, Lớp)', exact=True).click()
            page.get_by_role('heading', name='Thông tin sinh viên từ CTT').wait_for()
            page.get_by_role('cell', name='Bài thi tổng hợp', exact=True).wait_for()
            assert page.get_by_role('cell', name='0', exact=True).count() >= 1
            page.screenshot(path=str(output / 'english.png'), full_page=True)
            page.get_by_role('button', name='Học phí', exact=True).click()
            page.get_by_role('cell', name='Chưa có dữ liệu', exact=True).wait_for()
            page.get_by_role('cell', name='0 đ', exact=True).wait_for()
            sections['tuition'] = section(charges=[{'course_code':'ET2030','course_name':'Lập trình','amount':2800000}], payments=[{'label':'Học phí theo đăng ký học tập','amount':2800000,'actual_amount':2800000}], tables=[{'id':'fixture','headers':['Mã HP','Tổng tiền học phần'],'rows':[['ET2030','2,800,000 đ']]}])
            page.reload()
            page.get_by_role('button', name='Tiện ích CTT (Học phí, TOEIC, Lớp)', exact=True).click()
            page.get_by_role('button', name='Học phí', exact=True).click()
            page.get_by_role('heading', name='Học phí theo học phần', exact=True).wait_for()
            page.get_by_role('heading', name='Các khoản thu theo CTT', exact=True).wait_for()
            assert page.get_by_text('Chưa có dữ liệu đã đồng bộ để hiển thị.', exact=True).count() == 0
            assert page.get_by_text('Tổng khoản còn nợ trong các kỳ đã đọc được', exact=True).count() == 0
            assert page.locator('details.school-data-source[open]').count() == 0
            page.screenshot(path=str(output / 'tuition.png'), full_page=True)
            page.get_by_role('button', name='Bạn cùng lớp', exact=True).click()
            page.get_by_role('cell', name='Bạn cùng lớp kiểm thử', exact=True).wait_for()
            assert page.get_by_role('cell', name='Bạn cùng lớp kiểm thử', exact=True).count() == 1
            assert page.locator('details.school-data-source[open]').count() == 0
            page.screenshot(path=str(output / 'classmates.png'), full_page=True)
            page.get_by_role('button', name='Học vụ & Chứng chỉ', exact=True).click()
            page.get_by_text('Mức 0', exact=True).wait_for()
            page.get_by_text('Đã hoàn thành', exact=True).wait_for()
            page.get_by_text('Chưa hoàn thành', exact=True).wait_for()
            sections['certificates'] = section(source_type='coursework', requirements={'240':'unverified'}, coursework={
                key:{'status':'completed','passed_count':count,'required_count':count,'source_group_code':key,
                     'records':[{'course_code':f'{prefix}{i}','course_name':f'Học phần kiểm thử {key}-{i}','letter_grade':'D','is_passed':True} for i in range(count)],
                     'note':'Đối chiếu điểm chữ với các học phần trong nhóm CTĐT.'}
                for key,count,prefix in [('220',2,'PE10'),('230',4,'MIL12')]
            })
            page.reload()
            page.get_by_role('button', name='Tiện ích CTT (Học phí, TOEIC, Lớp)', exact=True).click()
            page.get_by_role('button', name='Học vụ & Chứng chỉ', exact=True).click()
            page.get_by_text('2/2 học phần đạt · Nhóm 220', exact=True).wait_for()
            page.get_by_text('4/4 học phần đạt · Nhóm 230', exact=True).wait_for()
            assert page.get_by_text('Đã hoàn thành học phần', exact=True).count() == 2
            page.get_by_role('heading',name='Căn cứ GDTC',exact=True).wait_for()
            page.get_by_role('heading',name='Căn cứ GDQP',exact=True).wait_for()
            page.screenshot(path=str(output / 'certificates.png'), full_page=True)
            page.get_by_role('button', name='Thời khóa biểu & Lịch thi', exact=True).click()
            page.get_by_role('heading', name='Chủ Nhật', exact=True).wait_for()
            page.get_by_text('ET2030 · Lập trình', exact=True).wait_for()
            page.screenshot(path=str(output / 'timetable.png'), full_page=True)
            page.get_by_role('button', name='Lịch thi', exact=True).click()
            page.get_by_label('Chọn PDF lịch thi').set_input_files({'name': 'fixture.pdf', 'mimeType': 'application/pdf', 'buffer': b'%PDF-fixture'})
            page.get_by_role('checkbox', name='Chọn ca thi 1').wait_for()
            assert not saved
            page.get_by_role('checkbox', name='Chọn ca thi 1').check()
            page.get_by_role('button', name='Xác nhận và lưu 1 ca thi đã chọn').click()
            page.get_by_text('Nhập PDF đã xác nhận', exact=True).wait_for()
            assert len(saved) == 1 and len(saved[0]['exams']) == 1
            assert saved[0]['exams'][0]['class_code'] == '123456'
            page.set_viewport_size({'width': 390, 'height': 844})
            close_sidebar = page.locator('[aria-label="Đóng thanh bên"]')
            close_sidebar.wait_for(state='visible')
            page.get_by_title('Thu gọn thanh bên', exact=True).click()
            close_sidebar.wait_for(state='hidden')
            page.screenshot(path=str(output / 'mobile-exams.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors, errors
            browser.close()
        print('PASS: zero score/debt, unknown values, classmates, warning 0, distinct certificate states, Sunday timetable, PDF preview and explicit selected-row import, mobile width.')
        print('Screenshots:', output)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__': main()
