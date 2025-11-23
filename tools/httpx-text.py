import os

def run_httpx_simple():
    command = './httpx -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0" -l url.txt -sc -title -server -td -fr -nc | tee -a httpxx.txt'

    try:
        exit_code = os.system(command)
        if exit_code == 0:
            print("命令执行成功！")
        else:
            print(f"命令执行失败，退出码: {exit_code}")
    except Exception as e:
        print(f"执行命令时出错: {e}")

if __name__ == "__main__":
    run_httpx_simple()