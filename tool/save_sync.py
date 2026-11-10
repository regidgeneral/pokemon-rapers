"""Đồng bộ code tool + file save giữa máy nhà và máy công ty qua MỘT repo GitHub riêng tư — Duy chốt 07/11.
Code ở nhánh chính (repo git của thư mục game); save ở nhánh 'save' (bản sao riêng trong <thư mục game>\\save_sync).
  py -3 save_sync.py setup <url>  lần đầu ở mỗi máy: nối code + save với repo GitHub
  py -3 save_sync.py start        TRƯỚC khi mở mGBA (Choi.bat): lấy code + save mới nhất về
  py -3 save_sync.py code         chỉ cập nhật code (nút ☁ Đồng bộ trong tool cũng làm việc này)
  py -3 save_sync.py pull         chỉ lấy save về (từ chối nếu mGBA đang chạy)
  py -3 save_sync.py push         đẩy save đang chơi lên (tool tự làm mỗi lần game lưu)
  py -3 save_sync.py status       xem giờ chơi bản ở máy / bản trên repo
Hai bản lệch nhau: bản có GIỜ CHƠI lâu hơn thắng, bản thua cất vào save_backup\\ (không xoá).
"""
import os, shutil, socket, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SAV_NAME = '2207 - Pokemon - Versione Smeraldo (I)(Pokemon Rapers).sav'
REPO_FILE = 'save.sav'
BRANCH = 'save'                      # save nằm ở nhánh riêng của repo GitHub; code ở nhánh chính (CodeSync)
NO_WINDOW = 0x08000000 if os.name == 'nt' else 0


def play_seconds(data):
    """Giờ chơi (giây) của bản lưu mới nhất trong file save FireRed (sector 0 = SaveBlock2); None nếu không đọc được."""
    best = None
    for slot in (0, 1):
        for i in range(14):
            o = slot * 0xE000 + i * 0x1000
            if o + 0x1000 > len(data):
                continue
            sid, _, sig, cnt = struct.unpack_from('<HHII', data, o + 0xFF4)
            if sid == 0 and sig == 0x08012025 and (best is None or cnt > best[0]):
                h, m, s = struct.unpack_from('<HBB', data, o + 0x0E)
                best = (cnt, h * 3600 + m * 60 + s)
    return best[1] if best else None


def fmt(sec):
    return '—' if sec is None else '%d:%02d:%02d' % (sec // 3600, sec // 60 % 60, sec % 60)


class SyncError(Exception):
    pass


class Sync:
    def __init__(self, root=None):
        self.root = root or os.path.dirname(HERE)
        self.sav = os.path.join(self.root, SAV_NAME)
        self.repo = os.path.join(self.root, 'save_sync')
        self.backup = os.path.join(self.root, 'save_backup')

    # --- git
    def git(self, *args, check=True):
        r = subprocess.run(['git', '-C', self.repo] + list(args), capture_output=True, text=True,
                           encoding='utf-8', errors='replace', creationflags=NO_WINDOW)
        if check and r.returncode:
            raise SyncError('git %s: %s' % (args[0], (r.stderr or r.stdout).strip()[-300:]))
        return r

    def ready(self):
        return os.path.isdir(os.path.join(self.repo, '.git'))

    def branch(self):
        return BRANCH

    def remote_bytes(self):
        """Nội dung save.sav trên remote (sau fetch); None nếu remote chưa có."""
        r = subprocess.run(['git', '-C', self.repo, 'show', 'origin/%s:%s' % (self.branch(), REPO_FILE)],
                           capture_output=True, creationflags=NO_WINDOW)            # nhị phân: không decode
        return None if r.returncode else r.stdout

    def local_bytes(self):
        try:
            with open(self.sav, 'rb') as f:
                return f.read()
        except OSError:
            return None

    @staticmethod
    def mgba_running():
        if os.name != 'nt' or os.environ.get('SAVE_SYNC_TEST_NO_MGBA'):   # biến này chỉ cho bài thử
            return False
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq mGBA.exe', '/NH'], capture_output=True, text=True,
                           creationflags=NO_WINDOW)
        return 'mgba.exe' in r.stdout.lower()

    # --- lệnh
    def init(self, url):
        """Nối repo save với nhánh BRANCH của repo GitHub (cùng repo với code, nhánh riêng)."""
        if self.ready():
            self.git('remote', 'set-url', 'origin', url)
            return 'Đã có repo save, đổi remote thành %s' % url
        os.makedirs(self.repo, exist_ok=True)
        self.git('init', '-q')
        self.git('remote', 'add', 'origin', url)
        self.git('fetch', 'origin')
        if not self.git('rev-parse', '--verify', 'origin/' + BRANCH, check=False).returncode:
            self.git('checkout', '-q', '-b', BRANCH, 'origin/' + BRANCH)
            return 'Đã nối repo save (nhánh %s).' % BRANCH
        self.git('checkout', '-q', '--orphan', BRANCH)        # repo chưa có nhánh save: tạo bằng bản ở máy này
        return self.push(first=True)

    def push(self, first=False):
        """Đẩy bản ở máy lên. Remote có bản giờ chơi lâu hơn -> không đè, báo (lần pull sau sẽ xử lý)."""
        if not self.ready():
            raise SyncError('chưa cài đồng bộ (py -3 save_sync.py init <url>)')
        data = self.local_bytes()
        if data is None or play_seconds(data) is None:
            raise SyncError('không đọc được %s' % self.sav)
        if not first:
            self.git('fetch', 'origin')
            rb = self.remote_bytes()
            if rb is not None and rb != data and (play_seconds(rb) or 0) > play_seconds(data):
                return 'KHÔNG đẩy: bản trên repo chơi lâu hơn (%s > %s). Đóng mGBA rồi chạy pull.' % (
                    fmt(play_seconds(rb)), fmt(play_seconds(data)))
            if rb is not None:                                # bản trên repo cũ hơn: lấy lịch sử của nó rồi đè lên
                self.git('reset', '--soft', 'origin/%s' % self.branch())
        dst = os.path.join(self.repo, REPO_FILE)
        try:
            with open(dst, 'rb') as f:
                same = f.read() == data
        except OSError:
            same = False
        if same and not first and not self.git('status', '--porcelain').stdout.strip() \
                and not self.git('rev-list', 'origin/%s..HEAD' % self.branch(), check=False).stdout.strip():
            return 'Repo đã có đúng bản này (%s).' % fmt(play_seconds(data))
        with open(dst, 'wb') as f:
            f.write(data)
        self.git('add', REPO_FILE)
        if self.git('diff', '--cached', '--quiet', check=False).returncode:
            self.git('-c', 'user.name=save-sync %s' % socket.gethostname(), '-c', 'user.email=save-sync@local',
                     'commit', '-m', 'Lưu %s — giờ chơi %s — máy %s' % (
                time.strftime('%Y-%m-%d %H:%M'), fmt(play_seconds(data)), socket.gethostname()))
        self.git('push', '-u', 'origin', self.branch())
        return 'Đã đẩy save lên (giờ chơi %s).' % fmt(play_seconds(data))

    def pull(self):
        """Lấy bản mới nhất về TRƯỚC khi mở mGBA. Bản ở máy chơi lâu hơn -> đẩy nó lên thay vì lấy về."""
        if not self.ready():
            raise SyncError('chưa cài đồng bộ (py -3 save_sync.py init <url>)')
        if self.mgba_running():
            raise SyncError('mGBA đang chạy: đóng mGBA rồi mới lấy save về (nếu không lần lưu sau sẽ đè mất).')
        self.git('fetch', 'origin')
        rb, lb = self.remote_bytes(), self.local_bytes()
        if rb is None:
            return self.push(first=True) if lb is not None else 'Repo trống và máy này chưa có save.'
        if lb == rb:
            self.git('reset', '--hard', 'origin/%s' % self.branch())
            return 'Save ở máy đã là bản mới nhất (%s).' % fmt(play_seconds(rb))
        pr, pl = play_seconds(rb) or 0, play_seconds(lb) if lb else None
        if pl is not None and pl > pr:
            return 'Bản ở máy chơi lâu hơn (%s > %s): ' % (fmt(pl), fmt(pr)) + self.push()
        if lb is not None:                                    # bản thua: cất đi, không xoá
            os.makedirs(self.backup, exist_ok=True)
            name = '%s_%s.sav' % (time.strftime('%Y%m%d-%H%M%S'), fmt(pl).replace(':', 'h', 1).replace(':', 'm'))
            shutil.copy2(self.sav, os.path.join(self.backup, name))
        self.git('reset', '--hard', 'origin/%s' % self.branch())
        shutil.copy2(os.path.join(self.repo, REPO_FILE), self.sav)
        return 'Đã lấy save mới nhất về (giờ chơi %s%s).' % (
            fmt(pr), '' if lb is None else '; bản cũ %s cất trong save_backup' % fmt(pl))

    def status(self):
        lines = ['Máy này: %s' % fmt(play_seconds(self.local_bytes() or b''))]
        if self.ready():
            self.git('fetch', 'origin', check=False)
            rb = self.remote_bytes()
            lines.append('Trên repo: %s' % (fmt(play_seconds(rb)) if rb else '(trống)'))
        else:
            lines.append('Chưa cài đồng bộ.')
        return '\n'.join(lines)


class CodeSync:
    """Code của tool = repo git ở thư mục game (nhánh chính), cùng repo GitHub với save (nhánh BRANCH)."""

    def __init__(self, root=None):
        self.root = root or os.path.dirname(HERE)

    def git(self, *args, check=True):
        r = subprocess.run(['git', '-C', self.root] + list(args), capture_output=True, text=True,
                           encoding='utf-8', errors='replace', creationflags=NO_WINDOW)
        if check and r.returncode:
            raise SyncError('git %s: %s' % (args[0], (r.stderr or r.stdout).strip()[-300:]))
        return r

    def ready(self):
        return os.path.isdir(os.path.join(self.root, '.git')) and \
            not self.git('remote', 'get-url', 'origin', check=False).returncode

    def branch(self):
        return self.git('rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()

    def init(self, url, branch='master'):
        """Máy đã có repo code (máy nhà): nối remote rồi đẩy lên. Máy chưa có (công ty: thư mục game có sẵn ROM,
        save, bản tool cũ): git init + lấy code về, ghi đè file của tool, KHÔNG đụng file không thuộc repo (ROM, save)."""
        if os.path.isdir(os.path.join(self.root, '.git')):
            if self.git('remote', 'get-url', 'origin', check=False).returncode:
                self.git('remote', 'add', 'origin', url)
            else:
                self.git('remote', 'set-url', 'origin', url)
            self.git('fetch', 'origin')
            if self.git('rev-parse', '--verify', 'origin/' + branch, check=False).returncode:
                self.git('push', '-u', 'origin', self.branch())   # repo GitHub chưa có code: đẩy bản máy này
                return 'Đã đẩy code lên (%s).' % self.branch()
            head = self.git('rev-parse', '--verify', 'HEAD', check=False)
            if not head.returncode and not self.git('merge-base', '--is-ancestor', 'origin/' + branch, 'HEAD',
                                                    check=False).returncode:
                self.git('push', '-u', 'origin', 'HEAD:' + branch)   # máy này mới hơn / bằng
                return 'Đã đẩy code lên (%s).' % branch
            note = ''
            if not head.returncode and self.git('merge-base', '--is-ancestor', 'HEAD', 'origin/' + branch,
                                                check=False).returncode:
                bk = 'truoc-dong-bo-' + time.strftime('%Y%m%d-%H%M%S')   # repo cũ lệch lịch sử: cất lại, không xoá
                self.git('branch', bk)
                note = ' Bản cũ của máy này cất ở nhánh %s.' % bk
            self.git('checkout', '-f', '-B', branch, 'origin/' + branch)
            self.git('branch', '--set-upstream-to', 'origin/' + branch)
            return 'Đã lấy code về (%s).%s' % (branch, note)
        self.git('init', '-q')
        self.git('remote', 'add', 'origin', url)
        self.git('fetch', 'origin')
        self.git('checkout', '-f', '-B', branch, 'origin/' + branch)
        return 'Đã lấy code về (%s).' % branch

    def update(self):
        """(số commit mới lấy về, câu báo). Có sửa chưa commit hoặc 2 bên lệch nhau thì không làm, báo."""
        if not self.ready():
            raise SyncError('chưa nối repo code (py -3 save_sync.py setup <url>)')
        br = self.branch()
        self.git('fetch', 'origin')
        if self.git('rev-parse', '--verify', 'origin/' + br, check=False).returncode:
            self.git('push', '-u', 'origin', br)
            return 0, 'Đã đẩy code lên (nhánh %s mới).' % br
        ahead, behind = map(int, self.git('rev-list', '--left-right', '--count',
                                          '%s...origin/%s' % (br, br)).stdout.split())
        if behind and self.git('status', '--porcelain', '-uno').stdout.strip():
            raise SyncError('có file tool đang sửa dở chưa commit, không lấy code mới về được')
        if ahead and behind:
            raise SyncError('code máy này và trên repo lệch nhau (%d / %d commit), cần gộp tay' % (ahead, behind))
        if behind:
            self.git('merge', '--ff-only', 'origin/' + br)
            return behind, 'Đã lấy %d bản sửa code mới về.' % behind
        if ahead:
            self.git('push', 'origin', br)
            return 0, 'Đã đẩy %d bản sửa code lên.' % ahead
        return 0, 'Code đã là bản mới nhất.'


def main(argv):
    cmds = ('init', 'pull', 'push', 'status', 'setup', 'code', 'start')
    if len(argv) < 2 or argv[1] not in cmds:
        print(__doc__)
        return 2
    s, c = Sync(), CodeSync()
    try:
        if argv[1] == 'setup':                            # lần đầu ở mỗi máy: code + save
            print(c.init(argv[2]))
            print(s.init(argv[2]))
        elif argv[1] == 'init':
            print(s.init(argv[2]))
        elif argv[1] == 'code':
            print(c.update()[1])
        elif argv[1] == 'start':                          # Choi.bat, trước khi mở mGBA: code + save mới nhất
            print(c.update()[1])
            print(s.pull())
        else:
            print(getattr(s, argv[1])())
    except (SyncError, IndexError) as e:
        print('LỖI:', e)
        return 1
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main(sys.argv))
