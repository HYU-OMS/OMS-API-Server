from app import app

if __name__ == "__main__":  # 테스트용 서버 run. 실제 서버는 이 코드로 동작하지 않음.
    app.run(host='0.0.0.0', port=8080)
