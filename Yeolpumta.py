import tkinter as tk
import threading
import time
import pyautogui
import keyboard
import cv2
import numpy as np
import mss

macro_running = False
box_x, box_y, box_w, box_h = 0, 0, 0, 0
nav_window = None

# 마우스를 화면 맨 왼쪽 위로 가져가면 강제 정지
pyautogui.FAILSAFE = True

# ==========================================
# 1. 춘구마 이미지 분석 로직
# ==========================================
def longest_black_line(gray):
    dark = (gray < 100).astype(np.uint8)
    kernel = np.ones((1, 3), np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, kernel)
    
    longest = 0
    for row in dark:
        current = 0
        for pixel in row:
            if pixel:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
    return longest

def classify(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape # 잘라낸 이미지의 높이와 너비를 가져옴
    
    # 가운데 춘구마 몸은 제외하고 양손 쪽만 확인 (비율은 그대로 유지)
    left_hand = gray[:, :int(width * 0.35)]
    right_hand = gray[:, int(width * 0.65):]
    
    left_line = longest_black_line(left_hand)
    right_line = longest_black_line(right_hand)
    
    longest = max(left_line, right_line)
    
    # 🌟 핵심: 절대 픽셀(35)이 아니라, 현재 잘라낸 이미지 '너비 대비 선의 비율'을 계산!
    ratio = longest / width 
    
    # 디버깅용 출력 (비율이 어떻게 나오는지 터미널에서 확인하세요)
    print(f"[분석] 선 길이: {longest}px, 너비 대비 비율: {ratio:.3f} ({(ratio*100):.1f}%)")
    
    # 비율을 기준으로 상태 판별 (예전 35px은 가로 325px 기준 약 10.7%였습니다)
    if ratio >= 0.08: # 🌟 8% 이상이면 물컵의 긴 가로선으로 인식
        return "물"
    elif ratio >= 0.02: # 🌟 2% ~ 8% 사이면 포크/나이프의 짧은 선으로 인식
        return "밥"
    else:
        # 2% 미만이면 빈 손(준비/대기 화면)
        return "대기"

def capture(sct, monitor):
    shot = sct.grab(monitor)
    return np.array(shot)[:, :, :3]

def image_difference(a, b):
    diff = cv2.absdiff(a, b)
    return np.mean(diff)

# ==========================================
# 2. UI 및 단축키 제어 로직
# ==========================================
def start_macro():
    global macro_running, box_x, box_y, box_w, box_h
    
    box_x = root.winfo_rootx()
    box_y = root.winfo_rooty()
    box_w = root.winfo_width()
    box_h = root.winfo_height()
    
    macro_running = True
    root.withdraw() 
    show_nav_bar()  
    
    print("▶ 매크로가 시작되었습니다. (정지: Space)")
    threading.Thread(target=macro_loop, daemon=True).start()

def show_nav_bar():
    global nav_window
    if nav_window is not None: return
    nav_window = tk.Toplevel(root)
    nav_window.overrideredirect(True)
    nav_window.attributes('-topmost', True)
    nav_window.configure(bg='#333333')
    
    nav_w, nav_h = 250, 40
    screen_w = nav_window.winfo_screenwidth()
    pos_x = (screen_w // 2) - (nav_w // 2)
    nav_window.geometry(f"{nav_w}x{nav_h}+{pos_x}+0")
    
    tk.Label(nav_window, text="▶ 매크로 실행 중 (정지: Space)", 
             fg="#4CAF50", bg="#333333", font=("맑은 고딕", 10, "bold")).pack(expand=True)

def trigger_stop():
    if macro_running:
        root.after(0, stop_macro) 

keyboard.add_hotkey('space', trigger_stop)

def stop_macro():
    global macro_running, nav_window
    macro_running = False
    if nav_window is not None:
        nav_window.destroy()
        nav_window = None
    root.deiconify() 
    print("■ 매크로 정지!")

# ==========================================
# 3. 메인 매크로 루프
# ==========================================
# ==========================================
# 3. 메인 매크로 루프
# ==========================================
# ==========================================
# 3. 메인 매크로 루프
# ==========================================
def macro_loop():
    global macro_running
    
    monitor = {
        "left": box_x,
        "top": box_y,
        "width": box_w,
        "height": box_h
    }
    
    yellow_btn_x = int(box_x + box_w * 0.75)
    yellow_btn_y = int(box_y + box_h * 0.95)

    center_x = int(box_x + box_w * 0.5)
    center_y = int(box_y + box_h * 0.5)
    print("🖱️ 해당 프로그램을 활성화하기 위해 화면 중앙을 클릭합니다.")
    pyautogui.click(center_x, center_y)
    time.sleep(0.5) 

    count = 0



    import mss
    with mss.mss() as sct:
        while macro_running:
            try:
                before = capture(sct, monitor)
                
                # 🌟 개선: 노란색 버튼을 '딱 1픽셀'이 아니라 '10x10 영역'으로 넓게 검사 (글자 겹침 방지)
                y_center = int(box_h * 0.95)
                x_center = int(box_w * 0.75)
                
                is_game_over = False
                # 화면 밖을 벗어나지 않게 안전장치
                if y_center + 5 < before.shape[0] and x_center + 5 < before.shape[1]:
                    # 10x10 픽셀 영역 잘라내기
                    patch = before[y_center-5:y_center+5, x_center-5:x_center+5]
                    
                    # B, G, R 분리 (OpenCV는 색상이 반대 순서임)
                    b_channel = patch[:, :, 0]
                    g_channel = patch[:, :, 1]
                    r_channel = patch[:, :, 2]
                    
                    # 10x10 영역 안에 노란색(R, G 높고 B 낮음)이 "단 하나라도(any)" 있는지 확인
                    yellow_mask = (r_channel > 180) & (g_channel > 180) & (b_channel < 100)
                    if np.any(yellow_mask):
                        is_game_over = True

                # 게임 오버 확인 시 클릭!
                if is_game_over: 
                    print("🔄 게임 종료 감지! '다시하기' 버튼을 클릭합니다.")
                    pyautogui.click(yellow_btn_x, yellow_btn_y)
                    
                    # 🌟 핵심: 클릭 직후 노란색이 없어지고 3, 2, 1 카운트다운이 끝날 때까지 넉넉히 대기!
                    print("⏳ '3, 2, 1, 시작!' 대기 중... (3.5초간 동작 정지)")
                    time.sleep(3.5) 
                    continue 
                
                # 🌟 회원님이 찾아내신 완벽한 크롭(Crop) 높이 비율 적용!
                top_y = int(box_h * 0.35)
                bottom_y = int(box_h * 0.50)
                
                cropped_img = before[top_y:bottom_y, :]
                
                # ==========================================
                # 🌟 [디버그 창 안전 출력 로직]
                cv2.imshow("Debug - Hands Only", cropped_img)
                
                # 창이 완벽하게 생성된 직후에 속성을 변경하고, 에러가 나면 무시하고 넘어감!
                try:
                    cv2.setWindowProperty("Debug - Hands Only", cv2.WND_PROP_TOPMOST, 0)
                except:
                    pass
                
                cv2.waitKey(1) 
                # ==========================================
                
                result = classify(cropped_img)
                
                if result == "대기":
                    time.sleep(0.1)
                    continue
                
                # ==========================================
                # 🌟 [사람처럼 행동하기 로직] 🌟
                
                # 1. 원래 눌러야 할 정답 키 결정
                target_key = 'right' if result == "물" else 'left'
                icon = "🥤" if result == "물" else "🍔"
                
                import random
                # 2. 2% 확률로 실수하기 (1~100 중 1, 2가 나오면 실수)
                is_mistake = random.randint(1, 100) <= 2
                if is_mistake:
                    # 키를 반대로 뒤집음
                    target_key = 'left' if target_key == 'right' else 'right'
                    print(f"{count+1}회: {result} {icon} -> 앗! 실수 발동 (2%) 🤪 -> {target_key} 키 입력")
                else:
                    print(f"{count+1}회: {result} {icon} -> 정상 -> {target_key} 키 입력")
                

                
                # 4. 실제 키보드 입력
                pyautogui.keyDown(target_key)
                time.sleep(0.05)
                pyautogui.keyUp(target_key)

                # 3. 누르기 직전 0 ~ 50ms(0.05초) 랜덤 대기
                random_delay = random.randint(0, 50) / 1000.0
                time.sleep(random_delay)
                # ==========================================
                
                count += 1
                
                changed = False
                start_wait = time.time()
                while macro_running and (time.time() - start_wait < 2.0): 
                    current = capture(sct, monitor)
                    difference = image_difference(before, current)
                    
                    if difference > 4: 
                        changed = True
                        break
                    time.sleep(0.01)
                
                if changed:
                    time.sleep(0.05)
                
            except Exception as e:
                print("에러 발생:", e)
                time.sleep(0.5)
# ==========================================
# 4. 프로그램 시작 (GUI 띄우기)
# ==========================================
root = tk.Tk()
root.title("춘구마 자동화 매크로")
root.geometry("400x550")
root.attributes('-alpha', 0.6) 
root.configure(bg='black')

lbl = tk.Label(root, text="이 창을 게임 화면에 딱 맞추세요.\n(하단 '게임 다시하기' 버튼까지 덮이게!)\n\n다 맞추면 아래 시작 버튼을 누르세요.", 
               fg="white", bg="black", font=("맑은 고딕", 12))
lbl.pack(expand=True)

btn = tk.Button(root, text="매크로 시작", command=start_macro, 
                font=("맑은 고딕", 12, "bold"), bg="#4CAF50", fg="white", height=2)
btn.pack(fill='x', side='bottom')

root.mainloop()