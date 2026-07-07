from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chess
import chess.engine
import os
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

board = chess.Board()

current_dir = os.path.dirname(os.path.abspath(__file__))

if os.name == 'nt':  # Windows'taysan lokal exe'yi kullan
    stockfish_path = os.path.join(current_dir, "stockfish.exe")
else:  # Render (Linux) üzerindeysek indirilen python paketinin yolunu otomatik bul
    from stockfish import Stockfish
    import shutil
    stockfish_path = shutil.which("stockfish") or "/usr/games/stockfish"

class MoveInput(BaseModel):
    source: str
    target: str
    promotion: Optional[str] = None

@app.post("/hamle-yap")
def make_move(data: MoveInput):
    global board
    
    move_uci = f"{data.source}{data.target}"
    if data.promotion:
        move_uci += data.promotion.lower()
    
    try:
        try:
            move = chess.Move.from_uci(move_uci)
        except:
            move = chess.Move.from_uci(move_uci + "q")
            
        if move not in board.legal_moves and len(move_uci) == 4:
            move = chess.Move.from_uci(move_uci + "q")

        if move in board.legal_moves:
            board.push(move)
            
            if not board.is_game_over():
                engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
                result = engine.play(board, chess.engine.Limit(time=0.1))
                ai_move = result.move
                board.push(ai_move)
                engine.quit()
                
                ai_move_str = ai_move.uci()
                bot_prom = ai_move_str[4:] if len(ai_move_str) > 4 else None
                
                return {
                    "durum": "basarili",
                    "kaynak": ai_move_str[:2],
                    "hedef": ai_move_str[2:4],
                    "bot_promotion": bot_prom
                }
            else:
                return {"durum": "oyun_bitti", "mesaj": "Oyun sona erdi!"}
        else:
            return {"durum": "hata", "mesaj": "Geçersiz hamle!"}
            
    except Exception as e:
        return {"durum": "hata", "mesaj": str(e)}

@app.post("/sifirla")
def reset_game():
    global board
    board.reset()
    return {"durum": "basarili", "mesaj": "Oyun sıfırlandı."}
