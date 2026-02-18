from __future__ import annotations

import copy
import math
import random
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox
from typing import Dict, List, Optional, Set, Tuple, FrozenSet

P1 = "X"
P2 = "O"
EMPTY = "."

# --- Graph (standard 24-point Nine Men's Morris) ---
ADJ: Dict[int, List[int]] = {
    0: [1, 9],
    1: [0, 2, 4],
    2: [1, 14],
    3: [4, 10],
    4: [1, 3, 5, 7],
    5: [4, 13],
    6: [7, 11],
    7: [4, 6, 8, 16],
    8: [7, 12],
    9: [0, 10, 21],
    10: [3, 9, 11, 18],
    11: [6, 10, 15],
    12: [8, 13, 17],
    13: [5, 12, 14, 20],
    14: [2, 13, 23],
    15: [11, 16],
    16: [7, 15, 17, 19],
    17: [12, 16],
    18: [10, 19],
    19: [16, 18, 20, 22],
    20: [13, 19],
    21: [9, 22],
    22: [19, 21, 23],
    23: [14, 22],
}

MILLS: List[Tuple[int, int, int]] = [
    (0, 1, 2), (0, 9, 21), (2, 14, 23), (21, 22, 23),
    (3, 4, 5), (3, 10, 18), (5, 13, 20), (18, 19, 20),
    (6, 7, 8), (6, 11, 15), (8, 12, 17), (15, 16, 17),
    (1, 4, 7), (9, 10, 11), (12, 13, 14), (16, 19, 22),
]
MILL_SETS = [set(m) for m in MILLS]


def other(p: str) -> str:
    return P2 if p == P1 else P1


def player_positions(board: List[str], p: str) -> List[int]:
    return [i for i, v in enumerate(board) if v == p]


def all_in_mills(board: List[str], p: str) -> Set[int]:
    s: Set[int] = set()
    for ms in MILL_SETS:
        if all(board[i] == p for i in ms):
            s |= ms
    return s


def is_mill(board: List[str], p: str, pos: int) -> bool:
    for ms in MILL_SETS:
        if pos in ms and all(board[i] == p for i in ms):
            return True
    return False


def completed_mills(board: List[str], p: str) -> Set[FrozenSet[int]]:
    out: Set[FrozenSet[int]] = set()
    for a, b, c in MILLS:
        if board[a] == p and board[b] == p and board[c] == p:
            out.add(frozenset((a, b, c)))
    return out


def phase(placed_x: int, placed_o: int) -> str:
    return "place" if (placed_x < 9 or placed_o < 9) else "move"


def can_fly(board: List[str], p: str) -> bool:
    return len(player_positions(board, p)) <= 3


def has_legal_move(board: List[str], p: str, placed_x: int, placed_o: int) -> bool:
    ph = phase(placed_x, placed_o)
    if ph == "place":
        return any(v == EMPTY for v in board)

    positions = player_positions(board, p)
    if len(positions) <= 3:
        return any(v == EMPTY for v in board)

    for frm in positions:
        for to in ADJ[frm]:
            if board[to] == EMPTY:
                return True
    return False


def winner(board: List[str], placed_x: int, placed_o: int) -> Optional[str]:
    x_count = board.count(P1)
    o_count = board.count(P2)

    if phase(placed_x, placed_o) == "move":
        if x_count < 3:
            return P2
        if o_count < 3:
            return P1
        if not has_legal_move(board, P1, placed_x, placed_o):
            return P2
        if not has_legal_move(board, P2, placed_x, placed_o):
            return P1
    return None


# --- AI ---
Move = Tuple


@dataclass
class State:
    board: List[str]
    to_move: str
    placed_x: int
    placed_o: int


def removable_positions(board: List[str], opponent: str) -> Set[int]:
    opp_pos = set(player_positions(board, opponent))
    if not opp_pos:
        return set()
    opp_in_mill = all_in_mills(board, opponent)
    non_mill = opp_pos - opp_in_mill
    return non_mill if non_mill else opp_pos


def generate_base_moves(st: State) -> List[Move]:
    b = st.board
    p = st.to_move
    ph = phase(st.placed_x, st.placed_o)

    moves: List[Move] = []
    if ph == "place":
        for i, v in enumerate(b):
            if v == EMPTY:
                moves.append(("place", i))
        return moves

    my_pos = player_positions(b, p)
    flying = len(my_pos) <= 3
    empties = [i for i, v in enumerate(b) if v == EMPTY]

    if flying:
        for frm in my_pos:
            for to in empties:
                moves.append(("move", frm, to))
    else:
        for frm in my_pos:
            for to in ADJ[frm]:
                if b[to] == EMPTY:
                    moves.append(("move", frm, to))
    return moves


def apply_base_move(st: State, mv: Move) -> Tuple[State, Optional[int]]:
    ns = State(board=st.board.copy(), to_move=st.to_move, placed_x=st.placed_x, placed_o=st.placed_o)
    p = st.to_move

    if mv[0] == "place":
        pos = mv[1]
        ns.board[pos] = p
        if p == P1:
            ns.placed_x += 1
        else:
            ns.placed_o += 1
        mill_pos = pos if is_mill(ns.board, p, pos) else None
        return ns, mill_pos

    if mv[0] == "move":
        frm, to = mv[1], mv[2]
        ns.board[frm] = EMPTY
        ns.board[to] = p
        mill_pos = to if is_mill(ns.board, p, to) else None
        return ns, mill_pos

    raise ValueError("Unknown move")


def generate_successors(st: State) -> List[Tuple[State, Move]]:
    succ: List[Tuple[State, Move]] = []
    p = st.to_move
    opp = other(p)

    for base in generate_base_moves(st):
        ns, mill_pos = apply_base_move(st, base)
        if mill_pos is not None:
            rem = removable_positions(ns.board, opp)
            if not rem:
                ns2 = copy.deepcopy(ns)
                ns2.to_move = opp
                succ.append((ns2, base))
            else:
                for r in rem:
                    ns2 = copy.deepcopy(ns)
                    ns2.board[r] = EMPTY
                    ns2.to_move = opp
                    succ.append((ns2, base + ("remove", r)))
        else:
            ns2 = ns
            ns2.to_move = opp
            succ.append((ns2, base))
    return succ


def evaluate(st: State, ai_player: str) -> float:
    w = winner(st.board, st.placed_x, st.placed_o)
    if w == ai_player:
        return 1e9
    if w == other(ai_player):
        return -1e9

    b = st.board
    p = ai_player
    o = other(ai_player)
    piece_diff = b.count(p) - b.count(o)
    my_mills = len(completed_mills(b, p))
    op_mills = len(completed_mills(b, o))
    return piece_diff * 100.0 + (my_mills - op_mills) * 60.0


def choose_ai_move(
    st: State,
    ai_player: str,
    depth: int = 3,
    no_repeat_block: Optional[Set[FrozenSet[int]]] = None,
) -> Move:
    """
    If no_repeat_block is provided, disallow moves that newly complete ANY mill in that set.
    (If everything is blocked, fall back to allowing it so the CPU never freezes.)
    """
    before_mills = completed_mills(st.board, ai_player)
    children_all = generate_successors(st)

    if no_repeat_block:
        filtered: List[Tuple[State, Move]] = []
        for child_state, mv in children_all:
            after_mills = completed_mills(child_state.board, ai_player)
            newly = after_mills - before_mills
            if newly & no_repeat_block:
                continue
            filtered.append((child_state, mv))
        children = filtered if filtered else children_all
    else:
        children = children_all

    children.sort(key=lambda it: 1 if ("remove" in it[1]) else 0, reverse=True)

    def alphabeta(node: State, d: int, a: float, b: float, maximizing: bool) -> float:
        w = winner(node.board, node.placed_x, node.placed_o)
        if d == 0 or w is not None:
            return evaluate(node, ai_player)

        ch = generate_successors(node)
        ch.sort(key=lambda it: 1 if ("remove" in it[1]) else 0, reverse=True)

        if maximizing:
            v = -math.inf
            for child, _mv in ch:
                v = max(v, alphabeta(child, d - 1, a, b, False))
                a = max(a, v)
                if a >= b:
                    break
            return v
        else:
            v = math.inf
            for child, _mv in ch:
                v = min(v, alphabeta(child, d - 1, a, b, True))
                b = min(b, v)
                if a >= b:
                    break
            return v

    best_score = -math.inf
    best_moves: List[Move] = []
    maximizing = (st.to_move == ai_player)

    for child_state, mv in children:
        score = alphabeta(child_state, depth - 1, -math.inf, math.inf, not maximizing)
        if score > best_score + 1e-9:
            best_score = score
            best_moves = [mv]
        elif abs(score - best_score) <= 1e-9:
            best_moves.append(mv)

    if not best_moves:
        return random.choice(generate_base_moves(st))
    return random.choice(best_moves)


# --- GUI Layout ---
NODE_POS: Dict[int, Tuple[int, int]] = {
    0: (60, 60),   1: (300, 60),   2: (540, 60),
    3: (140, 140), 4: (300, 140),  5: (460, 140),
    6: (220, 220), 7: (300, 220),  8: (380, 220),
    9: (60, 300),  10: (140, 300), 11: (220, 300),
    12: (380, 300), 13: (460, 300), 14: (540, 300),
    15: (220, 380), 16: (300, 380), 17: (380, 380),
    18: (140, 460), 19: (300, 460), 20: (460, 460),
    21: (60, 540),  22: (300, 540), 23: (540, 540),
}

EDGES: Set[Tuple[int, int]] = set()
for a, nbrs in ADJ.items():
    for b in nbrs:
        EDGES.add(tuple(sorted((a, b))))


RULES_TEXT = """Rules / How to Play

Goal:
• Make mills (3 in a row) to remove enemy pieces.
• Win when the opponent has fewer than 3 pieces OR has no legal moves (after placing ends).

Turn structure:
1) PLACE phase:
   • Each player places 9 pieces.
   • Click an empty node to place.

2) MOVE phase (after all 18 pieces placed):
   • Click your piece, then click where to move.
   • If you have more than 3 pieces: move to an ADJACENT node.
   • If you have exactly 3 pieces: you may FLY to ANY empty node.

Mills:
• If your move makes a mill, remove 1 opponent piece.
• Removal rule:
  – If the opponent has any pieces NOT in mills, remove one of those.
  – Otherwise you may remove a mill piece.
• Removable pieces are highlighted in PURPLE.

No Repeat option (v9 - fixed):
• When you make a mill, the game remembers ALL mills you created on that move.
• You may NOT create any of those SAME mills again later
  until you create a DIFFERENT mill (at least one different mill must be created first).
  This stops the classic open/close farming loop, even if a move creates 2 mills.

Hints:
• Blue = legal placements / destinations (vs CPU)
• Green = selected piece
• Purple = removable piece after a mill
• Click a selected piece again to unselect
"""


class MorrisGUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Nine Men's Morris (GUI)")

        self.canvas = tk.Canvas(self.root, width=600, height=600, bg="white")
        self.canvas.grid(row=0, column=0, rowspan=30, padx=10, pady=10)

        self.winner_var = tk.StringVar(value="")
        self.loser_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.winner_var, font=("Arial", 14, "bold"), fg="#0a7a0a").grid(
            row=0, column=1, sticky="w", padx=10, pady=(10, 0)
        )
        tk.Label(self.root, textvariable=self.loser_var, font=("Arial", 14, "bold"), fg="#a00000").grid(
            row=1, column=1, sticky="w", padx=10, pady=(0, 6)
        )

        self.status = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.status, justify="left").grid(row=2, column=1, sticky="nw", padx=10)

        self.mode = tk.StringVar(value="hvc")
        tk.Radiobutton(self.root, text="Human vs CPU", variable=self.mode, value="hvc").grid(row=3, column=1, sticky="w", padx=10)
        tk.Radiobutton(self.root, text="Human vs Human", variable=self.mode, value="hvh").grid(row=4, column=1, sticky="w", padx=10)

        tk.Label(self.root, text="CPU plays as:").grid(row=5, column=1, sticky="w", padx=10)
        self.cpu_as = tk.StringVar(value=P2)
        tk.Radiobutton(self.root, text="O", variable=self.cpu_as, value=P2).grid(row=6, column=1, sticky="w", padx=10)
        tk.Radiobutton(self.root, text="X", variable=self.cpu_as, value=P1).grid(row=7, column=1, sticky="w", padx=10)

        tk.Label(self.root, text="CPU strength:").grid(row=8, column=1, sticky="w", padx=10)
        self.cpu_depth = tk.IntVar(value=3)
        tk.Scale(self.root, from_=1, to=4, orient="horizontal", variable=self.cpu_depth).grid(row=9, column=1, sticky="we", padx=10)

        self.no_repeat = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.root,
            text="No Repeat (can't farm the same mill)",
            variable=self.no_repeat,
            onvalue=True,
            offvalue=False,
            wraplength=320,
            justify="left",
        ).grid(row=10, column=1, sticky="w", padx=10, pady=(8, 0))

        tk.Button(self.root, text="New Game", command=self.new_game).grid(row=11, column=1, sticky="we", padx=10, pady=(8, 0))
        tk.Button(self.root, text="Quit", command=self.root.destroy).grid(row=12, column=1, sticky="we", padx=10)

        tk.Label(self.root, text="Rules / How to Play", font=("Arial", 12, "bold")).grid(row=13, column=1, sticky="w", padx=10, pady=(14, 4))
        self.rules_box = tk.Text(self.root, width=42, height=18, wrap="word", padx=8, pady=8)
        self.rules_box.grid(row=14, column=1, rowspan=16, sticky="nsew", padx=10, pady=(0, 10))
        self.rules_box.insert("1.0", RULES_TEXT)
        self.rules_box.configure(state="disabled")

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(14, weight=1)

        self.st: State = State(board=[EMPTY] * 24, to_move=P1, placed_x=0, placed_o=0)
        self.selected_from: Optional[int] = None
        self.awaiting_removal: bool = False
        self.removal_allowed: Set[int] = set()
        self.legal_targets: Set[int] = set()
        self.last_action: str = ""

        self.node_items: Dict[int, int] = {}
        self.text_items: Dict[int, int] = {}
        self.game_over_popup_shown: bool = False

        # No-Repeat tracking:
        # stores ALL mills created on the last mill-forming move for each player
        self.last_mills_created_by: Dict[str, Set[FrozenSet[int]]] = {P1: set(), P2: set()}

        self.draw_board()
        self.update_ui()
        self.canvas.bind("<Button-1>", self.on_click)

    def run(self) -> None:
        self.new_game()
        self.root.mainloop()

    def is_cpu_turn(self) -> bool:
        return self.mode.get() == "hvc" and self.st.to_move == self.cpu_as.get()

    def show_hints(self) -> bool:
        return self.mode.get() == "hvc"

    def new_game(self) -> None:
        self.st = State(board=[EMPTY] * 24, to_move=P1, placed_x=0, placed_o=0)
        self.selected_from = None
        self.awaiting_removal = False
        self.removal_allowed = set()
        self.legal_targets = set()
        self.last_action = ""
        self.winner_var.set("")
        self.loser_var.set("")
        self.game_over_popup_shown = False
        self.last_mills_created_by = {P1: set(), P2: set()}
        self.update_ui()
        self.maybe_cpu_play()

    def draw_board(self) -> None:
        for a, b in sorted(EDGES):
            x1, y1 = NODE_POS[a]
            x2, y2 = NODE_POS[b]
            self.canvas.create_line(x1, y1, x2, y2, fill="#333", width=3)

        r = 16
        for i, (x, y) in NODE_POS.items():
            oval = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="white", outline="#111", width=2)
            txt = self.canvas.create_text(x, y, text="", font=("Arial", 14, "bold"))
            self.node_items[i] = oval
            self.text_items[i] = txt

        for i, (x, y) in NODE_POS.items():
            self.canvas.create_text(x, y + 26, text=str(i), font=("Arial", 9), fill="#666")

    def compute_legal_targets(self) -> Set[int]:
        if not self.show_hints() or self.awaiting_removal:
            return set()

        b = self.st.board
        p = self.st.to_move
        ph = phase(self.st.placed_x, self.st.placed_o)

        if ph == "place":
            return {i for i, v in enumerate(b) if v == EMPTY}

        if self.selected_from is None:
            return set()

        frm = self.selected_from
        if b[frm] != p:
            return set()

        if can_fly(b, p):
            return {i for i, v in enumerate(b) if v == EMPTY}
        return {to for to in ADJ[frm] if b[to] == EMPTY}

    def update_ui(self) -> None:
        b = self.st.board
        ph = phase(self.st.placed_x, self.st.placed_o)
        w = winner(b, self.st.placed_x, self.st.placed_o)

        if w:
            self.winner_var.set(f"WINNER: {w}")
            self.loser_var.set(f"LOSER: {other(w)}")
        else:
            self.winner_var.set("")
            self.loser_var.set("")

        self.legal_targets = self.compute_legal_targets()

        for i in range(24):
            piece = b[i]
            if piece == EMPTY:
                self.canvas.itemconfig(self.text_items[i], text="")
                self.canvas.itemconfig(self.node_items[i], fill="white")
            elif piece == P1:
                self.canvas.itemconfig(self.text_items[i], text="X")
                self.canvas.itemconfig(self.node_items[i], fill="#e6f0ff")
            else:
                self.canvas.itemconfig(self.text_items[i], text="O")
                self.canvas.itemconfig(self.node_items[i], fill="#ffe6e6")

            outline = "#111"
            width = 2
            if self.selected_from == i:
                outline = "#00aa00"
                width = 4
            self.canvas.itemconfig(self.node_items[i], outline=outline, width=width)

        for i in self.legal_targets:
            if self.selected_from == i:
                continue
            self.canvas.itemconfig(self.node_items[i], outline="#0066cc", width=4)

        for i in range(24):
            if self.awaiting_removal and i in self.removal_allowed:
                self.canvas.itemconfig(self.node_items[i], outline="#cc00cc", width=4)

        msg = []
        msg.append(f"Turn: {self.st.to_move}")
        msg.append(f"Phase: {ph.upper()}   (X placed {self.st.placed_x}/9, O placed {self.st.placed_o}/9)")
        msg.append(f"Pieces: X={b.count(P1)}  O={b.count(P2)}")
        msg.append(f"No Repeat: {'ON' if self.no_repeat.get() else 'OFF'}")

        if w:
            msg.append("Game Over! Start a New Game to play again.")
        elif self.awaiting_removal:
            msg.append("MILL! Click an opponent piece to remove (purple highlights).")
        elif ph == "move":
            msg.append("Click your piece, then click destination.")
        else:
            msg.append("Click an empty node to place.")

        if self.last_action:
            msg.append(f"Last: {self.last_action}")

        self.status.set("\n".join(msg))

        if w and not self.game_over_popup_shown:
            self.game_over_popup_shown = True
            messagebox.showinfo("Game Over", f"{w} wins!")

    def node_at(self, x: int, y: int) -> Optional[int]:
        for i, (nx, ny) in NODE_POS.items():
            if (x - nx) ** 2 + (y - ny) ** 2 <= 22 ** 2:
                return i
        return None

    def set_awaiting_removal(self, current_player: str) -> None:
        opp = other(current_player)
        self.awaiting_removal = True
        self.removal_allowed = removable_positions(self.st.board, opp)
        self.selected_from = None
        self.legal_targets = set()

    def finish_turn_switch(self) -> None:
        self.st.to_move = other(self.st.to_move)
        self.selected_from = None
        self.awaiting_removal = False
        self.removal_allowed = set()
        self.legal_targets = set()
        self.update_ui()
        self.maybe_cpu_play()

    def maybe_cpu_play(self) -> None:
        if winner(self.st.board, self.st.placed_x, self.st.placed_o):
            return
        if not self.is_cpu_turn():
            return
        self.root.after(200, self.cpu_play)

    # --- No Repeat helpers (v9) ---
    def no_repeat_blocks(self, player: str, newly: Set[FrozenSet[int]]) -> bool:
        if not self.no_repeat.get():
            return False
        blocked = self.last_mills_created_by[player]
        return bool(newly & blocked)

    def update_no_repeat_memory(self, player: str, newly: Set[FrozenSet[int]]) -> None:
        """If player formed mills this move, remember ALL of them as the 'blocked' set.
        If player did not form mills, do nothing (keep memory so open/close is still blocked later).
        """
        if newly:
            self.last_mills_created_by[player] = set(newly)

    # --- CPU ---
    def cpu_play(self) -> None:
        if winner(self.st.board, self.st.placed_x, self.st.placed_o):
            return
        if not self.is_cpu_turn():
            return

        ai_player = self.cpu_as.get()
        blockset = self.last_mills_created_by[ai_player] if self.no_repeat.get() else None

        before = completed_mills(self.st.board, ai_player)
        mv = choose_ai_move(self.st, ai_player, depth=self.cpu_depth.get(), no_repeat_block=blockset)
        self.apply_encoded_move(mv, actor=ai_player)
        after = completed_mills(self.st.board, ai_player)
        newly = after - before
        self.update_no_repeat_memory(ai_player, newly)

        self.update_ui()
        self.finish_turn_switch()

    def apply_encoded_move(self, mv: Move, actor: str) -> None:
        if mv[0] == "place":
            pos = mv[1]
            self.st.board[pos] = actor
            if actor == P1:
                self.st.placed_x += 1
            else:
                self.st.placed_o += 1
            self.last_action = f"{actor} placed at {pos}"
            if len(mv) >= 4 and mv[2] == "remove":
                r = mv[3]
                self.st.board[r] = EMPTY
                self.last_action += f" and removed {r}"
            return

        if mv[0] == "move":
            frm, to = mv[1], mv[2]
            self.st.board[frm] = EMPTY
            self.st.board[to] = actor
            self.last_action = f"{actor} moved {frm}->{to}"
            if len(mv) >= 5 and mv[3] == "remove":
                r = mv[4]
                self.st.board[r] = EMPTY
                self.last_action += f" and removed {r}"
            return

        raise ValueError("bad move encoding")

    # --- Human input ---
    def on_click(self, event: tk.Event) -> None:
        if winner(self.st.board, self.st.placed_x, self.st.placed_o):
            return
        if self.is_cpu_turn():
            return

        idx = self.node_at(event.x, event.y)
        if idx is None:
            return

        b = self.st.board
        p = self.st.to_move
        opp = other(p)
        ph = phase(self.st.placed_x, self.st.placed_o)

        # removal
        if self.awaiting_removal:
            if idx in self.removal_allowed and b[idx] == opp:
                b[idx] = EMPTY
                self.last_action = f"{p} removed opponent at {idx}"
                self.update_ui()
                self.finish_turn_switch()
            return

        # place
        if ph == "place":
            if b[idx] != EMPTY:
                return

            before = completed_mills(b, p)
            b[idx] = p
            if p == P1:
                self.st.placed_x += 1
            else:
                self.st.placed_o += 1
            after = completed_mills(b, p)
            newly = after - before

            if self.no_repeat_blocks(p, newly):
                b[idx] = EMPTY
                if p == P1:
                    self.st.placed_x -= 1
                else:
                    self.st.placed_o -= 1
                self.last_action = "No Repeat: form a different mill first."
                self.update_ui()
                return

            self.last_action = f"{p} placed at {idx}"

            if is_mill(b, p, idx):
                self.update_no_repeat_memory(p, newly)
                self.set_awaiting_removal(p)
                self.update_ui()
                return

            self.update_ui()
            self.finish_turn_switch()
            return

        # move phase: toggle unselect / switch selection
        if self.selected_from is not None and idx == self.selected_from:
            self.selected_from = None
            self.update_ui()
            return
        if b[idx] == p:
            self.selected_from = idx
            self.update_ui()
            return
        if self.selected_from is None:
            return

        frm = self.selected_from
        to = idx

        if b[to] != EMPTY:
            return
        if not can_fly(b, p) and to not in ADJ[frm]:
            return
        if (self.show_hints() and self.legal_targets) and (to not in self.legal_targets):
            return

        before = completed_mills(b, p)
        b[frm] = EMPTY
        b[to] = p
        after = completed_mills(b, p)
        newly = after - before

        if self.no_repeat_blocks(p, newly):
            b[to] = EMPTY
            b[frm] = p
            self.last_action = "No Repeat: form a different mill first."
            self.update_ui()
            return

        self.last_action = f"{p} moved {frm}->{to}"
        self.selected_from = None

        if is_mill(b, p, to):
            self.update_no_repeat_memory(p, newly)
            self.set_awaiting_removal(p)
            self.update_ui()
            return

        self.update_ui()
        self.finish_turn_switch()


if __name__ == "__main__":
    MorrisGUI().run()
