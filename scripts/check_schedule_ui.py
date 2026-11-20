"""Check schedule month calendar and agenda views with synthetic API data."""
import functools
import json
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright
from check_auth_ui import QuietHandler, ROOT


def main():
    output = Path(tempfile.gettempdir()) / 'schedule-ui'
    output.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'frontend/dist')))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    account = {
        'student_id': '20221234',
        'student_name': 'Sinh viên kiểm thử',
        'class_name': 'Lớp thử - K67',
        'program_code': 'ET1',
        'auth_provider': 'ctt',
    }

    def section(records=None, **extra):
        return {
            'status': 'synced',
            'synced_at': '2026-11-15T00:00:00Z',
            'source_url': 'https://ctt-sis.hust.edu.vn/',
            'records': records or [],
            'tables': [],
            **extra,
        }

    timetable_records = [
        {
            'id': 'rec-1',
            'course_code': 'PH3330',
            'course_name': 'Vật lý điện tử',
            'class_code': '173759',
            'room': 'D9-502',
            'day_of_week': 6,  # Thứ 6
            'start_period': 1,
            'end_period': 3,
            'time_str': '12:30 - 14:55',
            'weeks': '2-9,11-18',
            'lecturer': 'TS. Nguyễn Văn Giả',
            'is_temp': False,
        },
        {
            'id': 'rec-2',
            'course_code': 'ET2030',
            'course_name': 'Kỹ thuật lập trình',
            'class_code': '123456',
            'room': 'D3-201',
            'day_of_week': 2,  # Thứ 2 sáng
            'start_period': 1,
            'end_period': 3,
            'time_str': '08:00 - 10:25',
            'weeks': '1,3,5,7,9,11,13,15',
            'lecturer': 'TS. Trần Văn Thử',
            'is_temp': False,
        },
        {
            'id': 'rec-3',
            'course_code': 'IT3040',
            'course_name': 'Kỹ thuật phần mềm',
            'class_code': '789012',
            'room': 'D5-101',
            'day_of_week': 3,
            'start_period': 4,
            'end_period': 6,
            'time_str': '10:35 - 13:00',
            'weeks': 'chưa có tuần cụ thể',  # Cột tuần không đọc được
            'lecturer': 'ThS. Lê Văn Test',
            'is_temp': False,
        },
    ]

    exam_records = [
        {
            'course_code': 'PH3330',
            'course_name': 'Vật lý điện tử',
            'class_code': '173759',
            'exam_date': '08/01/2027',
            'exam_time': '07:30',
            'room': 'D9-502',
            'exam_type': 'Tự luận',
            'student_index': '042',
        }
    ]

    sections = {
        'english': section([]),
        'tuition': section([]),
        'classmates': section([]),
        'warning': section(warning_level=0),
        'certificates': section(),
        'timetable': section(timetable_records),
        'temporary_timetable': section(status='empty'),
        'exams': section(exam_records),
    }

    errors = []

    def api(route):
        path = route.request.url.split('/api/', 1)[1]
        data = {}
        if path == 'auth/me':
            data = account
        elif path == 'student/profile':
            data = {'info': account, 'transcript': [], 'school_sync': {'synced_at': 'fixture'}}
        elif path == 'student/audit':
            data = {'student_info': account, 'cpa': 3.5, 'total_credits_required': 126, 'total_credits_accumulated': 30}
        elif path == 'student/school-services':
            data = {'sections': sections}
        elif path == 'conversations':
            data = {'conversations': []}
        route.fulfill(content_type='application/json', body=json.dumps(data))

    screenshots = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chromium', headless=True)
            page = browser.new_page(viewport={'width': 1280, 'height': 800})
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('**/api/**', api)

            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.get_by_role('button', name='Thời khóa biểu & Lịch thi', exact=True).click()

            # 1. Verify unplaced warning banner
            page.locator('.schedule-warning-banner').wait_for()
            assert 'IT3040' in page.locator('.schedule-warning-banner').inner_text()

            # 2. Open November 2026
            month_select = page.get_by_label('Chọn tháng')
            year_select = page.get_by_label('Chọn năm')
            month_select.select_option('10')  # November (0-based index 10)
            year_select.select_option('2026')

            # 3. Select 20/11/2026 (Friday week 12)
            btn_nov20 = page.locator('button[aria-label*="20/11/2026"]')
            btn_nov20.wait_for()
            btn_nov20.click()

            # Check card details: 173759 - Vật lý điện tử
            page.locator('.schedule-card', has_text='173759 - Vật lý điện tử').wait_for()
            card_text = page.locator('.schedule-card', has_text='173759 - Vật lý điện tử').inner_text()
            assert '12:30 - 14:55' in card_text
            assert 'Tuần 12' in card_text
            assert 'Chiều Thứ 6' in card_text

            # 4. Check 13/11/2026 (week 11) - should have class
            btn_nov13 = page.locator('button[aria-label*="13/11/2026"]')
            btn_nov13.click()
            page.locator('.schedule-card', has_text='173759 - Vật lý điện tử').wait_for()

            # 5. Check 06/11/2026 (week 10, not in 2-9,11-18) - should NOT have class
            btn_nov06 = page.locator('button[aria-label*="06/11/2026"]')
            btn_nov06.click()
            assert page.locator('.schedule-card', has_text='173759 - Vật lý điện tử').count() == 0

            # 6. Check January 2027 (08/01/2027 has exam)
            month_select.select_option('0')  # January
            year_select.select_option('2027')
            btn_jan08 = page.locator('button[aria-label*="08/01/2027"]')
            btn_jan08.wait_for()
            btn_jan08.click()

            # Check exam card
            page.locator('.schedule-card--exam', has_text='Vật lý điện tử').wait_for()
            exam_text = page.locator('.schedule-card--exam').inner_text()
            assert '07:30' in exam_text
            assert 'Lịch thi' in exam_text

            # 7. Test Arrow keys navigation
            btn_jan08.focus()
            page.keyboard.press('ArrowRight')
            btn_jan09 = page.locator('button[aria-label*="09/01/2027"]')
            assert btn_jan09.get_attribute('aria-selected') == 'true'

            # 8. Screenshots: 1280x800 Dark
            # Reset back to Nov 20, 2026 for rich screenshot
            month_select.select_option('10')
            year_select.select_option('2026')
            page.locator('button[aria-label*="20/11/2026"]').click()

            desktop_dark = output / 'schedule-desktop-dark.png'
            page.screenshot(path=str(desktop_dark))
            screenshots['desktop_dark'] = str(desktop_dark)

            # 1280x800 Light
            page.evaluate("document.body.classList.add('light-theme')")
            desktop_light = output / 'schedule-desktop-light.png'
            page.screenshot(path=str(desktop_light))
            screenshots['desktop_light'] = str(desktop_light)

            # 9. Test mobile 375x812 responsive layout
            page.set_viewport_size({'width': 375, 'height': 812})
            close_sidebar = page.locator('[aria-label="Đóng thanh bên"]')
            if close_sidebar.is_visible():
                page.get_by_title('Thu gọn thanh bên', exact=True).click()

            # Check no horizontal scrolling
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')

            mobile_light = output / 'schedule-mobile-light.png'
            page.screenshot(path=str(mobile_light))
            screenshots['mobile_light'] = str(mobile_light)

            # 375x812 Dark
            page.evaluate("document.body.classList.remove('light-theme')")
            mobile_dark = output / 'schedule-mobile-dark.png'
            page.screenshot(path=str(mobile_dark))
            screenshots['mobile_dark'] = str(mobile_dark)

            assert not errors, errors
            browser.close()

        print('PASS: Schedule month calendar and day agenda verified.')
        print('Screenshots:')
        for k, v in screenshots.items():
            print(f'  {k}: {v}')

    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
