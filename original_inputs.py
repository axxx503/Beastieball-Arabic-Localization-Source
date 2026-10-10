from pathlib import Path
import hashlib,json,os
R=Path(__file__).resolve().parent
GAME=Path(os.environ.get('BEASTIEBALL_GAME','H:/SteamLibrary/steamapps/common/Beastieball'))
EXPECTED=json.loads((R/'SUPPORTED-ORIGINALS.json').read_text('utf8'))
def original_input(relative):
 expected=EXPECTED[relative]
 for p in [GAME/relative,GAME/'.beastieball-arabic-backup'/relative]:
  if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==expected:return p
 raise RuntimeError('Supported pristine original unavailable: '+relative)
