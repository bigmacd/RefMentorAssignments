#!/usr/bin/env python3
"""
NiceGUI-based Referee Mentor System
Converted from Streamlit version
"""

import os
import sys
from datetime import datetime as dtime
from typing import Tuple
from contextlib import redirect_stdout
from io import StringIO

from nicegui import ui, app

# Add parent directory to path to import existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import RefereeDbCockroach
from excelWriter import getExcelFromText
from auth_nicegui import AuthManager, require_auth
from uiData import getAllData
from main import run


# Global state
class AppState:
    def __init__(self):
        self.auth_manager = AuthManager()
        self.db = RefereeDbCockroach()
        self.all_match_data = None
        self.dates = []
        self.current_tab = "Enter a Mentor Report"

    def load_data(self):
        if self.all_match_data is None:
            self.all_match_data = getAllData()
            self.dates = list(self.all_match_data.keys())


state = AppState()


def parse_ref_name(name: str) -> Tuple[str, str]:
    """Parse referee name handling various formats"""
    if name == '(requested)':
        return (None, None)

    name = ' '.join(name.split())
    parts = name.split(',')
    if len(parts) > 1:
        first_parts = parts[1].strip().split()
        return (first_parts[0], parts[0].strip())

    parts = name.split(' ')
    if len(parts) == 0:
        return (None, None)
    elif len(parts) == 1:
        return (parts[0], "")
    elif len(parts) == 2:
        return (parts[0], parts[1])
    else:
        suffixes = ["Jr.", "Jr", "Sr.", "Sr", "III", "IV", "II"]
        if parts[-1] in suffixes:
            return (parts[0], ' '.join(parts[1:-1]) + ' ' + parts[-1])
        else:
            return (parts[0], ' '.join(parts[1:]))


def get_current_date_index(dates: list) -> int:
    fs = "%A, %B %d, %Y"
    today = dtime.now()
    fd = today.strftime(fs)
    today = dtime.strptime(fd, fs)
    for index, d in enumerate(dates):
        this_date = dtime.strptime(d, fs)
        if this_date >= today:
            return index
    return 0


@ui.page('/')
def main_page():
    require_auth(state.auth_manager)
    state.load_data()

    # Custom CSS
    ui.add_head_html('''
    <style>
        .tab-button {
            padding: 12px 24px;
            margin: 4px;
            border-radius: 8px;
            font-weight: 500;
        }
        .tab-button.active {
            background-color: #1976d2 !important;
            color: white !important;
        }
        .form-container {
            width: 100% !important;
            max-width: none !important;
            padding: 20px;
        }
        .checkbox-row {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
    </style>
    ''')

    with ui.header().classes('bg-blue-900 text-white'):
        ui.label('🏆 Referee Mentor System').classes('text-2xl font-bold')

    # Left sidebar for user menu
    with ui.left_drawer(top_corner=True, bottom_corner=True).classes('p-4') as drawer:
        ui.label(f'Logged in as:').classes('text-gray-600 text-sm')
        ui.label(f'{state.auth_manager.get_current_user()}').classes('font-bold mb-2')
        ui.label(f'Role: {state.auth_manager.get_user_role()}').classes('text-gray-600 text-sm mb-4')

        ui.separator()

        ui.button('Change Password', on_click=lambda: ui.navigate.to('/change-password')).classes('w-full mt-4').props('flat')
        ui.button('Logout', on_click=lambda: state.auth_manager.logout()).classes('w-full mt-2').props('flat color=red')

        if state.auth_manager.is_admin():
            ui.separator().classes('my-4')
            ui.label('Admin Functions').classes('font-bold text-sm')
            ui.button('User Management', on_click=lambda: ui.navigate.to('/admin/users')).classes('w-full mt-2').props('flat')

        ui.separator().classes('my-4')
        dark = ui.dark_mode()
        dark.bind_value(app.storage.user, 'dark_mode')
        ui.switch('Dark Mode').bind_value(app.storage.user, 'dark_mode')

    # Tab navigation
    with ui.row().classes('w-full justify-center p-4'):
        tabs = [
            ("📥 Enter a Mentor Report", "Enter a Mentor Report"),
            ("📤 Generate Reports", "Generate Reports"),
            ("📝 See Current Workload", "See Current Workload"),
        ]

        tab_buttons = {}
        for icon_label, tab_id in tabs:
            btn = ui.button(icon_label, on_click=lambda t=tab_id: switch_tab(t))
            btn.classes('tab-button')
            tab_buttons[tab_id] = btn

    # Content container
    content = ui.column().classes('w-full p-4')

    def switch_tab(tab_id):
        state.current_tab = tab_id
        content.clear()
        with content:
            if tab_id == "Enter a Mentor Report":
                render_mentor_report_tab()
            elif tab_id == "Generate Reports":
                render_reports_tab()
            elif tab_id == "See Current Workload":
                render_workload_tab()

        # Update button styles
        for tid, btn in tab_buttons.items():
            if tid == tab_id:
                btn.classes(add='active')
            else:
                btn.classes(remove='active')

    # Initial render
    switch_tab(state.current_tab)


def render_mentor_report_tab():
    """Render the mentor report entry form"""

    # Form state
    form_state = {
        'mentor': None,
        'date': None,
        'venue': None,
        'game': None,
        'center_cb': False,
        'ar1_cb': False,
        'ar2_cb': False,
        'revisit_center': False,
        'revisit_ar1': False,
        'revisit_ar2': False,
        'comments': '',
        'current_match': None
    }

    with ui.card().classes('form-container w-full'):
        ui.label('Enter a Mentor Report').classes('text-xl font-bold mb-4')

        # Mentor selection
        mentors = state.db.getMentors()
        mentor_values = sorted([f'{m[0].capitalize()} {m[1].capitalize()}' for m in mentors])

        # Filter to current user if not admin
        current_user = state.auth_manager.get_current_user()
        if current_user and not current_user.startswith('martin'):
            filtered = [v for v in mentor_values if v.lower().startswith(current_user.lower())]
            if filtered:
                mentor_values = filtered

        mentor_select = ui.select(mentor_values, label='Select Mentor', value=mentor_values[0] if mentor_values else None)
        mentor_select.classes('w-full')

        # Date selection
        date_index = get_current_date_index(state.dates)
        if date_index < len(state.dates) and state.dates[date_index].startswith('Tuesday'):
            date_index = min(date_index + 1, len(state.dates) - 1)

        date_select = ui.select(state.dates, label='Select Date', value=state.dates[date_index] if state.dates else None)
        date_select.classes('w-full')

        # Venue selection (dynamic based on date)
        venue_select = ui.select([], label='Select Venue')
        venue_select.classes('w-full')

        # Game selection (dynamic based on venue)
        game_select = ui.select([], label='Select Game')
        game_select.classes('w-full')

        # Referee checkboxes container
        ui.label('Select referees being mentored:').classes('mt-4 font-semibold')
        ref_container = ui.row().classes('checkbox-row')

        center_cb = ui.checkbox('Center: --')
        ar1_cb = ui.checkbox('AR1: --')
        ar2_cb = ui.checkbox('AR2: --')

        # Comments
        comments = ui.textarea(label='Comments', placeholder='Enter your mentoring comments here...').classes('w-full mt-4')
        comments.props('rows=10')

        # Revisit checkboxes
        ui.label('Should any referee be revisited?').classes('mt-4 font-semibold')
        with ui.row().classes('checkbox-row'):
            revisit_center = ui.checkbox('Revisit Center')
            revisit_ar1 = ui.checkbox('Revisit AR1')
            revisit_ar2 = ui.checkbox('Revisit AR2')

        # Message area
        message_area = ui.column().classes('w-full mt-4')

        def update_venues():
            selected_date = date_select.value
            if selected_date and selected_date in state.all_match_data:
                matches = state.all_match_data[selected_date]
                venues = sorted(list(matches.keys()))
                venue_select.options = venues
                venue_select.value = venues[0] if venues else None
                update_games()

        def update_games():
            selected_date = date_select.value
            selected_venue = venue_select.value
            if selected_date and selected_venue and selected_date in state.all_match_data:
                matches = state.all_match_data[selected_date]
                if selected_venue in matches:
                    games = matches[selected_venue]
                    game_options = [f"Time-{g['Time']}" for g in games]
                    game_select.options = game_options
                    game_select.value = game_options[0] if game_options else None
                    update_refs()

        def update_refs():
            selected_date = date_select.value
            selected_venue = venue_select.value
            selected_game = game_select.value

            if not all([selected_date, selected_venue, selected_game]):
                return

            matches = state.all_match_data.get(selected_date, {})
            games = matches.get(selected_venue, [])

            game_time = selected_game.split('-')[1] if selected_game else None
            current_match = None
            for g in games:
                if g['Time'] == game_time:
                    current_match = g
                    break

            form_state['current_match'] = current_match

            if current_match:
                center_cb.text = f"Center: {current_match.get('Center', '--')}"
                ar1_cb.text = f"AR1: {current_match.get('AR1', '--')}"
                ar2_cb.text = f"AR2: {current_match.get('AR2', '--')}"

        date_select.on_value_change(lambda: update_venues())
        venue_select.on_value_change(lambda: update_games())
        game_select.on_value_change(lambda: update_refs())

        # Initial load
        update_venues()

        def do_save():
            current_match = form_state['current_match']
            if not current_match:
                with message_area:
                    ui.notify('Please select a game first', type='warning')
                return

            mentor = mentor_select.value
            if not mentor:
                ui.notify('Please select a mentor', type='warning')
                return

            refs = [center_cb.value, ar1_cb.value, ar2_cb.value]
            positions = ['Center', 'AR1', 'AR2']

            if not any(refs):
                ui.notify('Please select at least one referee', type='warning')
                return

            for i, ref_selected in enumerate(refs):
                if ref_selected:
                    ref_name = current_match[positions[i]]
                    revisit = (positions[i] == "Center" and revisit_center.value) or \
                              (positions[i] == "AR1" and revisit_ar1.value) or \
                              (positions[i] == "AR2" and revisit_ar2.value)

                    status, message = state.db.addMentorSessionNew(
                        mentor.lower(),
                        ref_name.lower(),
                        positions[i],
                        date_select.value,
                        comments.value,
                        revisit,
                        current_match.get('GameID', '')
                    )

                    if status:
                        ui.notify(f'{message}: Referee {ref_name}', type='positive')
                    else:
                        ui.notify(f'Error: {message}', type='negative')

            # Reset form
            center_cb.value = False
            ar1_cb.value = False
            ar2_cb.value = False
            revisit_center.value = False
            revisit_ar1.value = False
            revisit_ar2.value = False
            comments.value = ''

        def do_cancel():
            center_cb.value = False
            ar1_cb.value = False
            ar2_cb.value = False
            revisit_center.value = False
            revisit_ar1.value = False
            revisit_ar2.value = False
            comments.value = ''

        # Buttons
        with ui.row().classes('w-full justify-between mt-4'):
            ui.button('Save', on_click=do_save).props('color=primary')
            ui.button('Cancel', on_click=do_cancel).props('color=grey')


def render_reports_tab():
    """Render the reports generation tab"""

    with ui.card().classes('form-container w-full'):
        ui.label('Generate Reports').classes('text-xl font-bold mb-4')

        # Report format
        format_select = ui.radio(['Text', 'Excel'], value='Text').props('inline')

        # Report type
        year_data = state.db.getYears()
        year_data.insert(0, ' ')

        report_type = ui.select(
            ['by year', 'by week', 'by referee', 'by mentor'],
            label='Report Type',
            value='by year'
        ).classes('w-full')

        # Dynamic selection container
        selection_container = ui.column().classes('w-full')

        # Download area
        download_area = ui.column().classes('w-full mt-4')

        current_selection = {'type': None, 'value': None}

        def update_selection():
            selection_container.clear()
            download_area.clear()

            with selection_container:
                if report_type.value == 'by year':
                    sel = ui.select(year_data, label='Select Year').classes('w-full')
                    sel.on_value_change(lambda: set_selection('year', sel.value))

                elif report_type.value == 'by week':
                    weeks = [' '] + state.dates
                    sel = ui.select(weeks, label='Select Week').classes('w-full')
                    sel.on_value_change(lambda: set_selection('week', sel.value))

                elif report_type.value == 'by referee':
                    referees = [' '] + state.db.getRefereesForSelectionBox()
                    sel = ui.select(referees, label='Select Referee').classes('w-full')
                    sel.on_value_change(lambda: set_selection('referee', sel.value))

                elif report_type.value == 'by mentor':
                    mentors = [' '] + state.db.getMentorsForSelectionBox()
                    sel = ui.select(mentors, label='Select Mentor').classes('w-full')
                    sel.on_value_change(lambda: set_selection('mentor', sel.value))

        def set_selection(sel_type, value):
            current_selection['type'] = sel_type
            current_selection['value'] = value
            update_download_button()

        def update_download_button():
            download_area.clear()

            if not current_selection['value'] or current_selection['value'] == ' ':
                return

            with download_area:
                ui.button('Generate Report', on_click=generate_report).props('color=primary')

        def generate_report():
            sel_type = current_selection['type']
            sel_value = current_selection['value']
            report_format = format_select.value

            if not sel_value or sel_value == ' ':
                ui.notify('Please make a selection', type='warning')
                return

            try:
                if sel_type == 'year':
                    data = state.db.produceYearReport(sel_value, report_format)
                elif sel_type == 'week':
                    data = state.db.produceWeekReport(sel_value, report_format)
                elif sel_type == 'referee':
                    data = state.db.produceRefereeReport(sel_value, report_format)
                elif sel_type == 'mentor':
                    data = state.db.produceMentorReport(sel_value, report_format)
                else:
                    return

                if report_format == 'Text':
                    ui.download(data.encode(), f'report.txt')
                else:
                    getExcelFromText(data)
                    with open('report.xlsx', 'rb') as f:
                        ui.download(f.read(), 'report.xlsx')

            except Exception as e:
                ui.notify(f'Error generating report: {str(e)}', type='negative')

        report_type.on_value_change(lambda: update_selection())
        update_selection()


def render_workload_tab():
    """Render the current workload tab"""

    with ui.card().classes('form-container w-full'):
        ui.label('Current Workload').classes('text-xl font-bold mb-4')

        output_area = ui.code('Loading...').classes('w-full')

        def load_workload():
            try:
                # Capture stdout from the run() function
                stdout_capture = StringIO()
                with redirect_stdout(stdout_capture):
                    run()
                output = stdout_capture.getvalue()
                output_area.content = output if output else 'No workload data available'
            except Exception as e:
                output_area.content = f'Error loading workload: {str(e)}'

        ui.timer(0.1, load_workload, once=True)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title='Referee Mentor System',
        port=8080,
        reload=False,
        show=True,
        storage_secret=os.environ.get('STORAGE_SECRET', 'referee-mentor-secret-key-change-in-production')
    )

