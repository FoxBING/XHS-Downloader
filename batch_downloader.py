import asyncio
import random
import sys
import re
import sqlite3
import io
from contextlib import redirect_stdout
from pathlib import Path
from source import XHS
from source.module import Settings, ROOT

PROJECT_ROOT = ROOT.parent
TXT_FILE_PATH = PROJECT_ROOT / "1.txt"
FAILED_TXT_PATH = PROJECT_ROOT / "failed.txt"
EXPLORE_DB_PATH = ROOT / "ExploreID.db"


def extract_id_from_url(url):
    match = re.search(r'/item/([a-f0-9]+)\?', url)
    return match.group(1) if match else None


def read_downloaded_ids():
    if not EXPLORE_DB_PATH.exists():
        return set()
    conn = sqlite3.connect(str(EXPLORE_DB_PATH))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ID FROM explore_id")
        return {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()


def read_links_from_1txt():
    try:
        with open(TXT_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        lines = content.split('\n')
        links = []
        for line in lines:
            parts = line.split()
            for part in parts:
                if part.strip():
                    links.append(part.strip())
        return links
    except Exception as e:
        print(f"读取1.txt文件出错: {e}")
        return []


def save_failed_links(failed_links):
    if not failed_links:
        return
    try:
        with open(FAILED_TXT_PATH, 'w', encoding='utf-8') as f:
            for link in failed_links:
                f.write(link + '\n')
        print(f"\n已将 {len(failed_links)} 个失败链接保存到 {FAILED_TXT_PATH}")
    except Exception as e:
        print(f"保存失败链接出错: {e}")


def parse_statistics(output):
    pattern = r'共处理 (\d+) 个作品，成功 (\d+) 个，失败 (\d+) 个，跳过 (\d+) 个'
    match = re.search(pattern, output)
    if match:
        return {
            'all': int(match.group(1)),
            'success': int(match.group(2)),
            'fail': int(match.group(3)),
            'skip': int(match.group(4))
        }
    return None


async def download_link(xhs, link):
    print(f"\n{'='*50}")
    print(f"正在处理链接: {link}")

    output_buffer = io.StringIO()

    try:
        with redirect_stdout(output_buffer):
            await xhs.extract_cli(link, download=True, index=None, data=False)

        output = output_buffer.getvalue()
        print(output)
        stats = parse_statistics(output)

        if stats:
            if stats['fail'] > 0:
                print(f"处理失败: 失败 {stats['fail']} 个")
                return False, False
            elif stats['skip'] > 0:
                print(f"处理跳过: 跳过 {stats['skip']} 个")
                return False, True
            else:
                print(f"处理成功: 成功 {stats['success']} 个")
                return True, False
        else:
            print(f"处理成功")
            return True, False
    except Exception as e:
        error_msg = str(e)
        print(f"处理出错: {error_msg}")

        if "'browser_cookie'" in error_msg:
            print("检测到配置错误（browser_cookie），将跳过等待时间继续处理下一个链接")
            return False, True
        else:
            return False, False


async def main():
    print(f"{'='*60}")
    print(f"小红书随机间隔批量下载器 - 直接调用API")
    print(f"下载间隔: 随机 30-60 秒")
    print(f"{'='*60}")

    links = read_links_from_1txt()
    if not links:
        print("\n错误：未找到有效链接或文件读取失败！")
        return

    print(f"\n成功读取到 {len(links)} 个链接")

    downloaded_ids = read_downloaded_ids()
    if downloaded_ids:
        before = len(links)
        filtered = []
        skipped_existing = 0
        for link in links:
            item_id = extract_id_from_url(link)
            if item_id and item_id in downloaded_ids:
                skipped_existing += 1
            else:
                filtered.append(link)
        links = filtered
        print(f"数据库中共有 {len(downloaded_ids)} 条下载记录")
        print(f"过滤前 {before} 个链接，过滤后 {len(links)} 个待下载")
        if skipped_existing > 0:
            print(f"已跳过 {skipped_existing} 个已下载的作品（零网络请求）")
    else:
        print("未找到下载记录数据库，将处理所有链接")
        print(f"（首次运行或数据库路径不存在: {EXPLORE_DB_PATH}）")

    if not links:
        print("\n所有链接均已下载，无需处理！")
        return

    settings = Settings(ROOT)
    params = settings.run()
    xhs = XHS(**params)

    failed_links = []
    success_count = 0
    skip_count = 0

    async with xhs:
        for i, link in enumerate(links, 1):
            print(f"\n{'-'*60}")
            print(f"开始处理链接 {i}/{len(links)}")

            success, skipped = await download_link(xhs, link)

            if success:
                success_count += 1
            elif skipped:
                skip_count += 1
            else:
                failed_links.append(link)

            if i < len(links):
                if skipped:
                    print("\n直接处理下一个链接...")
                else:
                    wait_time = random.randint(30, 60)
                    print(f"\n随机等待 {wait_time} 秒后处理下一个链接...")
                    for remaining in range(wait_time, 0, -1):
                        sys.stdout.write(f"倒计时: {remaining}秒\r")
                        sys.stdout.flush()
                        await asyncio.sleep(1)
                    print("\n")

    print(f"\n{'='*60}")
    print(f"所有链接处理完成！")
    print(f"成功: {success_count}, 跳过: {skip_count}, 失败: {len(failed_links)}")
    print(f"{'='*60}")

    save_failed_links(failed_links)


if __name__ == "__main__":
    asyncio.run(main())
