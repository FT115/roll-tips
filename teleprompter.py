"""
全屏滚动提词器
============
运行此脚本后，全屏显示提词内容，文字自下而上滚动。
文字滚动完毕后停留一段时间自动退出。
按 ESC 或 Q 可随时退出。
"""

import sys
import os
import time
import pygame
from config import (
    FULLSCREEN,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    BACKGROUND_COLOR,
    TEXT_COLOR,
    FONT_SIZE,
    FONT_PATH,
    LINE_SPACING,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
    MARGIN_BOTTOM,
    SCROLL_SPEED,
    DELAY_BEFORE_START,
    WAIT_AFTER_END,
    WORDS_FILE,
    FILE_ENCODING,
)


def find_chinese_font():
    """查找可用的中文字体，优先使用用户指定的字体路径。"""
    if FONT_PATH and os.path.exists(FONT_PATH):
        return FONT_PATH

    # Windows 常见中文字体路径
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/simsun.ttc",     # 宋体
        "C:/Windows/Fonts/simkai.ttf",     # 楷体
        "C:/Windows/Fonts/msyhbd.ttc",     # 微软雅黑粗体
    ]
    for path in candidates:
        if os.path.exists(path):
            return path

    return None  # 使用 pygame 默认字体


def load_text(filepath, encoding="utf-8"):
    """从文件中加载提词文本。"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(script_dir, filepath)
    with open(full_path, "r", encoding=encoding) as f:
        return f.read().strip()


def wrap_text(text, font, max_width):
    """
    将文本按屏幕宽度自动换行。
    对中文文本，尽量不在标点符号前断行。
    """
    lines = []
    current_line = ""
    # 不应作为行首的标点符号
    no_line_start = set("，。！？；：、》》）」』】〗\"'）")

    for char in text:
        if char == "\n":
            lines.append(current_line)
            current_line = ""
            continue

        # 跳过回车符
        if char == "\r":
            continue

        test_line = current_line + char
        # 检查是否超出宽度
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            # 当前行已满，保存并开始新行
            if current_line:
                lines.append(current_line)
            current_line = char

    if current_line:
        lines.append(current_line)

    # 如果所有行都为空，至少保留一个空行
    return lines if lines else [""]


def main():
    # ============ 初始化 pygame ============
    pygame.init()

    # 隐藏鼠标
    pygame.mouse.set_visible(False)

    # ============ 设置显示 ============
    if FULLSCREEN:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME)
        screen_width, screen_height = screen.get_size()
    else:
        screen_width, screen_height = WINDOW_WIDTH, WINDOW_HEIGHT
        screen = pygame.display.set_mode((screen_width, screen_height))

    pygame.display.set_caption("滚动提词器")

    # ============ 加载字体 ============
    font_file = find_chinese_font()
    try:
        if font_file:
            font = pygame.font.Font(font_file, FONT_SIZE)
        else:
            font = pygame.font.Font(None, FONT_SIZE)
    except Exception:
        print(f"警告: 无法加载字体 {font_file}，使用默认字体")
        font = pygame.font.Font(None, FONT_SIZE)

    # 获取字体行高
    line_height = font.get_linesize()
    line_step = line_height + LINE_SPACING  # 每行的总高度

    # ============ 加载并排版文字 ============
    raw_text = load_text(WORDS_FILE, FILE_ENCODING)
    text_width = screen_width - MARGIN_LEFT - MARGIN_RIGHT
    lines = wrap_text(raw_text, font, text_width)

    if not lines:
        print("错误: words.txt 中没有文字内容")
        pygame.quit()
        sys.exit(1)

    total_text_height = len(lines) * line_step

    # ============ 预渲染所有行 ============
    # 提前渲染为 surface，避免每帧重复渲染
    line_surfaces = []
    for line in lines:
        # 抗锯齿渲染
        surf = font.render(line, True, TEXT_COLOR)
        line_surfaces.append(surf)

    # ============ 滚动参数 ============
    # 可视区域
    visible_top = MARGIN_TOP
    visible_bottom = screen_height - MARGIN_BOTTOM

    # 起始位置：第一行在可视区域底部（文字从屏幕下方进入）
    start_scroll_y = float(visible_bottom)
    # 结束位置：最后一行滚出可视区域顶部
    end_scroll_y = float(visible_top - total_text_height)

    scroll_y = start_scroll_y
    clock = pygame.time.Clock()

    # ============ 状态机 ============
    STATE_WAITING = "waiting"      # 等待开始
    STATE_SCROLLING = "scrolling"  # 正在滚动
    STATE_FINISHED = "finished"    # 滚动完毕，停留等待

    state = STATE_WAITING
    state_start_time = time.time()

    # ============ 主循环 ============
    running = True
    while running:
        # ---- 事件处理 ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                # 空格键暂停/继续
                elif event.key == pygame.K_SPACE:
                    if state == STATE_SCROLLING:
                        state = STATE_WAITING
                        state_start_time = time.time()
                    elif state == STATE_WAITING:
                        state = STATE_SCROLLING
                        state_start_time = time.time()

        # ---- 状态更新 ----
        dt = clock.get_time() / 1000.0  # 转换为秒

        if state == STATE_WAITING:
            elapsed = time.time() - state_start_time
            if elapsed >= DELAY_BEFORE_START:
                state = STATE_SCROLLING
                state_start_time = time.time()

        elif state == STATE_SCROLLING:
            # 更新滚动位置
            scroll_y -= SCROLL_SPEED * dt

            # 检查是否滚动完毕
            if scroll_y <= end_scroll_y:
                scroll_y = end_scroll_y
                state = STATE_FINISHED
                state_start_time = time.time()

        elif state == STATE_FINISHED:
            elapsed = time.time() - state_start_time
            if elapsed >= WAIT_AFTER_END:
                running = False

        # ---- 绘制 ----
        screen.fill(BACKGROUND_COLOR)

        # 只绘制在可视区域内的行
        for i, surf in enumerate(line_surfaces):
            line_y = int(scroll_y + i * line_step)
            # 裁剪：只绘制可见的行
            if line_y + line_height < visible_top:
                continue
            if line_y > visible_bottom:
                continue

            # 行在屏幕上的 X 位置（居中）
            line_x = MARGIN_LEFT
            screen.blit(surf, (line_x, line_y))

        # ---- 进度指示器（底部小横条） ----
        if state == STATE_SCROLLING:
            total_scroll = start_scroll_y - end_scroll_y
            if total_scroll > 0:
                progress = (start_scroll_y - scroll_y) / total_scroll
                bar_width = int(screen_width * 0.3)
                bar_height = 3
                bar_x = (screen_width - bar_width) // 2
                bar_y = screen_height - 20
                # 背景条
                pygame.draw.rect(screen, (60, 60, 60),
                                 (bar_x, bar_y, bar_width, bar_height))
                # 进度条
                filled = int(bar_width * progress)
                if filled > 0:
                    pygame.draw.rect(screen, (100, 100, 100),
                                     (bar_x, bar_y, filled, bar_height))

        # ---- 刷新画面 ----
        pygame.display.flip()
        clock.tick(60)  # 60 FPS

    # ============ 清理 ============
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
