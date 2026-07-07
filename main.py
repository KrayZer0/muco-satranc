from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chess
import chess.engine
import os
import shutil
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

# SİSTEMDE HAZIR MOTOR VAR MI DİYE KONTROL EDİLİYOR
if os.name == 'nt':  # Windows
    stockfish_path = os.path.join(current_dir, "stockfish.exe")
else:  # Linux (Render)
    # Sistem yollarını kontrol et, yoksa varsayılanı bırak
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
                if os.name != 'nt':
                    try:
                        # HATA ALAN YER BURASIYDI: Kütüphaneyi ham parametreyle başlatıyoruz
                        from stockfish import Stockfish
                        sf = Stockfish(path=None) # Herhangi bir dış dosyaya bağımlı kalma, kendi içindekini kullan!
                        sf.set_fen_position(board.fen())
                        best_move_str = sf.get_best_move()
                        ai_move = chess.Move.from_uci(best_move_str)
                    except Exception:
                        # Eğer kütüphane yöntemi yine de bulamazsa standart satranç motoruyla dene
                        engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
                        result = engine.play(board, chess.engine.Limit(time=0.1))
                        ai_move = result.move
                        engine.quit()
                else:
                    # Windows (Lokal makinen için)
                    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
                    result = engine.play(board, chess.engine.Limit(time=0.1))
                    ai_move = result.move
                    engine.quit()

                board.push(ai_move)
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
