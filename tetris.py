# ========================================================================
# Aurausp Maneshni | Arizona State University | Python for Engineers     #
# Final Project Tetris Game Demo                                         #
# Now updated to work with Github pages                                  #
# ========================================================================

from js import document, window
from pyodide.ffi import create_proxy
import random
import time

# Proxy globals so Python doesn't throw them away lol 
start_proxy = None
pause_proxy = None
restart_proxy = None
keydown_proxy = None
canvas_click_proxy = None
tick_proxy = None

# Board size 
COLS = 10
ROWS = 20

# Size of each tile in pixels
TILE = 30

# Get canvas and drawing context from the page
canvas = document.getElementById("game")
ctx = canvas.getContext("2d")

# Make canvas match the board size
canvas.width = COLS * TILE
canvas.height = ROWS * TILE

# Let canvas be focused so keyboard input works
canvas.setAttribute("tabindex", "0")

# Score display elements
score_el = document.getElementById("score")
lines_el = document.getElementById("lines")
level_el = document.getElementById("level")

# Buttons
start_btn = document.getElementById("btn-start")
pause_btn = document.getElementById("btn-pause")
restart_btn = document.getElementById("btn-restart")

# Colors for each piece type
COLORS = {
    "I": "#00f0f0",
    "J": "#0000f0",
    "L": "#f0a000",
    "O": "#f0f000",
    "S": "#00f000",
    "T": "#a000f0",
    "Z": "#f00000",
}

# Shapes made with 1 and 0
# 1 means there is a block there
# 0 means empty
PIECES = {
    "I": [[1, 1, 1, 1]],
    "J": [[1, 0, 0],
          [1, 1, 1]],
    "L": [[0, 0, 1],
          [1, 1, 1]],
    "O": [[1, 1],
          [1, 1]],
    "S": [[0, 1, 1],
          [1, 1, 0]],
    "T": [[0, 1, 0],
          [1, 1, 1]],
    "Z": [[1, 1, 0],
          [0, 1, 1]],
}

# GAME STATE
board = []              # 2D list with 0 or piece letter
active_kind = ""        # current piece letter
active_shape = []       # current piece matrix
active_x = 0            # current piece left position
active_y = 0            # current piece top position

score = 0
lines_cleared = 0
level = 1

is_running = False
is_paused = False

drop_interval = 0.8     # seconds between automatic drops
last_time = time.time() # used to time drops

# SIMPLE HELPERS
def copy_shape(shape):
    # Make a fresh copy so rotations do not affect the original
    new_shape = []
    for row in shape:
        new_shape.append(row[:])
    return new_shape


def make_empty_board():
    # Create a board full of zeros
    new_board = []
    r = 0
    while r < ROWS:
        new_board.append([0] * COLS)
        r = r + 1
    return new_board


def pick_random_piece():
    # Choose a random piece kind
    kinds = list(PIECES.keys())
    kind = random.choice(kinds)

    # Copy its shape so we can rotate it
    shape = copy_shape(PIECES[kind])

    # Spawn near the middle
    x = COLS // 2 - len(shape[0]) // 2
    y = -1

    return kind, shape, x, y


def rotate_clockwise(shape):
    # Rotate the matrix clockwise (simple beginner style)
    new_shape = []
    width = len(shape[0])
    height = len(shape)

    c = 0
    while c < width:
        new_row = []
        r = height - 1
        while r >= 0:
            new_row.append(shape[r][c])
            r = r - 1
        new_shape.append(new_row)
        c = c + 1

    return new_shape


def collides(shape, x, y):
    # True means it hits a wall, floor, or another block
    r = 0
    while r < len(shape):
        c = 0
        while c < len(shape[r]):
            if shape[r][c] == 1:
                br = y + r
                bc = x + c

                # Left and right walls
                if bc < 0 or bc >= COLS:
                    return True

                # Floor
                if br >= ROWS:
                    return True

                # Existing blocks
                if br >= 0:
                    if board[br][bc] != 0:
                        return True

            c = c + 1
        r = r + 1

    return False


def update_speed():
    # Make game faster when level increases
    global drop_interval

    drop_interval = 0.8 - (level - 1) * 0.06
    if drop_interval < 0.1:
        drop_interval = 0.1


# DRAWING
def draw_block(x, y, color):
    # Draw one tile
    ctx.fillStyle = color
    ctx.fillRect(x * TILE, y * TILE, TILE - 1, TILE - 1)


def draw_everything():
    # Clear background
    ctx.fillStyle = "#0b0b0b"
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    # Draw locked blocks
    r = 0
    while r < ROWS:
        c = 0
        while c < COLS:
            cell = board[r][c]
            if cell != 0:
                draw_block(c, r, COLORS[cell])
            c = c + 1
        r = r + 1

    # Draw the active piece
    if active_kind != "":
        r = 0
        while r < len(active_shape):
            c = 0
            while c < len(active_shape[r]):
                if active_shape[r][c] == 1:
                    yy = active_y + r
                    xx = active_x + c
                    if yy >= 0:
                        draw_block(xx, yy, COLORS[active_kind])
                c = c + 1
            r = r + 1

    # If paused show a simple overlay
    if is_running and is_paused:
        ctx.fillStyle = "rgba(0,0,0,0.55)"
        ctx.fillRect(0, 0, canvas.width, canvas.height)

        ctx.fillStyle = "#ffffff"
        ctx.font = "bold 22px system-ui, sans-serif"
        ctx.textAlign = "center"
        ctx.fillText("Paused", canvas.width // 2, canvas.height // 2)


def update_hud():
    score_el.textContent = str(score)
    lines_el.textContent = str(lines_cleared)
    level_el.textContent = str(level)


def show_game_over():
    # Dark overlay
    ctx.fillStyle = "rgba(0,0,0,0.65)"
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    # Text
    ctx.fillStyle = "#ffffff"
    ctx.font = "bold 28px system-ui, sans-serif"
    ctx.textAlign = "center"
    ctx.fillText("Game Over", canvas.width // 2, canvas.height // 2 - 10)

    ctx.font = "16px system-ui, sans-serif"
    msg = "Score " + str(score) + "  Lines " + str(lines_cleared)
    ctx.fillText(msg, canvas.width // 2, canvas.height // 2 + 20)



# GAME LOGIC 
def spawn_piece():
    # Create the next falling piece
    global active_kind, active_shape, active_x, active_y
    global is_running

    kind, shape, x, y = pick_random_piece()
    active_kind = kind
    active_shape = shape
    active_x = x
    active_y = y

    # If it collides right away, the stack is too high
    if collides(active_shape, active_x, active_y):
        is_running = False
        draw_everything()
        show_game_over()


def clear_full_lines():
    # Remove lines that are completely filled
    global board, score, lines_cleared, level

    new_board = []
    cleared_now = 0

    r = 0
    while r < ROWS:
        # A row is full if there is no 0 in it
        if 0 not in board[r]:
            cleared_now = cleared_now + 1
        else:
            new_board.append(board[r])
        r = r + 1

    # Add empty rows to the top
    while len(new_board) < ROWS:
        new_board.insert(0, [0] * COLS)

    board = new_board

    # Update score and level
    if cleared_now > 0:
        lines_cleared = lines_cleared + cleared_now

        # Simple scoring
        score = score + (cleared_now * 100 * level)

        level = 1 + (lines_cleared // 10)
        update_speed()


def lock_piece():
    # Copy the active piece into the board
    global last_time

    r = 0
    while r < len(active_shape):
        c = 0
        while c < len(active_shape[r]):
            if active_shape[r][c] == 1:
                br = active_y + r
                bc = active_x + c

                # If we lock above the visible board, game over
                if br < 0:
                    end_game()
                    return

                board[br][bc] = active_kind

            c = c + 1
        r = r + 1

    clear_full_lines()
    spawn_piece()

    # Reset the drop timer so the new piece does not instantly drop
    last_time = time.time()


def end_game():
    global is_running
    is_running = False
    draw_everything()
    show_game_over()


def move_left():
    global active_x
    if not collides(active_shape, active_x - 1, active_y):
        active_x = active_x - 1


def move_right():
    global active_x
    if not collides(active_shape, active_x + 1, active_y):
        active_x = active_x + 1


def move_down():
    global active_y
    if not collides(active_shape, active_x, active_y + 1):
        active_y = active_y + 1
    else:
        lock_piece()


def hard_drop():
    global active_y
    while not collides(active_shape, active_x, active_y + 1):
        active_y = active_y + 1
    lock_piece()


def rotate_piece():
    global active_shape, active_x, active_y

    rotated = rotate_clockwise(active_shape)

    # Simple wall help
    tries = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]

    i = 0
    while i < len(tries):
        ox, oy = tries[i]
        if not collides(rotated, active_x + ox, active_y + oy):
            active_shape = rotated
            active_x = active_x + ox
            active_y = active_y + oy
            return
        i = i + 1


# INPUT
def on_keydown(evt):
    global is_paused

    key = evt.key

    # Pause toggle always works while running
    if key == "p" or key == "P":
        if is_running:
            is_paused = not is_paused
        return

    if not is_running:
        return

    if is_paused:
        return

    if key == "ArrowLeft":
        move_left()
    elif key == "ArrowRight":
        move_right()
    elif key == "ArrowDown":
        move_down()
    elif key == "ArrowUp":
        rotate_piece()
    elif key == " ":
        hard_drop()



# BUTTONS
def start_game(event=None):
    # Start only if not currently running
    if not is_running:
        reset_game()
    canvas.focus()


def pause_game(event=None):
    global is_paused
    if not is_running:
        return
    is_paused = not is_paused
    canvas.focus()


def restart_game(event=None):
    reset_game()
    canvas.focus()


def reset_game():
    global board, score, lines_cleared, level
    global is_running, is_paused
    global last_time
    global active_kind, active_shape, active_x, active_y

    board = make_empty_board()

    score = 0
    lines_cleared = 0
    level = 1

    is_running = True
    is_paused = False

    update_speed()

    active_kind = ""
    active_shape = []
    active_x = 0
    active_y = 0

    spawn_piece()

    last_time = time.time()



# MAIN LOOP
def tick():
    global last_time

    if not is_running:
        draw_everything()
        update_hud()
        return

    if is_paused:
        draw_everything()
        update_hud()
        return

    now = time.time()

    # Automatic drop
    if now - last_time >= drop_interval:
        last_time = now
        move_down()

    draw_everything()
    update_hud()

# BOOT
def boot():
    global board
    global start_proxy, pause_proxy, restart_proxy, keydown_proxy, canvas_click_proxy, tick_proxy

    board = make_empty_board()
    update_speed()

    draw_everything()
    update_hud()

    # Wrap Python functions so JavaScript can safely call them later
    start_proxy = create_proxy(start_game)
    pause_proxy = create_proxy(pause_game)
    restart_proxy = create_proxy(restart_game)
    keydown_proxy = create_proxy(on_keydown)
    canvas_click_proxy = create_proxy(lambda e: canvas.focus())
    tick_proxy = create_proxy(tick)

    # Connect buttons
    start_btn.addEventListener("click", start_proxy)
    pause_btn.addEventListener("click", pause_proxy)
    restart_btn.addEventListener("click", restart_proxy)

    # Connect keyboard
    document.addEventListener("keydown", keydown_proxy)

    # Click canvas to focus it
    canvas.addEventListener("click", canvas_click_proxy)

    # Run the game loop
    window.setInterval(tick_proxy, 16)

    
boot()
