import json

notebook = {
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "provenance": []
    },
    "kernelspec": {
      "name": "python3",
      "display_name": "Python 3"
    },
    "language_info": {
      "name": "python"
    }
  },
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "markdown-1"
      },
      "source": [
        "# 🎬 숏폼 영상 자동화 공장 (Google Colab 버전)\n\n",
        "PC방이나 스마트폰, 태블릿 등 어디서든 웹 브라우저만 있으면 접속 가능한 버전입니다.\n",
        "아래 두 개의 셀(Cell) 좌측에 있는 **재생(▶) 버튼**을 순서대로 눌러서 실행해주세요."
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {
        "id": "code-1"
      },
      "outputs": [],
      "source": [
        "# 1. 구글 드라이브 마운트 (결과물 저장을 위해 필요합니다. 접근 권한을 허용해주세요)\n",
        "from google.colab import drive\n",
        "drive.mount('/content/drive')\n",
        "\n",
        "# 2. 최신 프로그램 다운로드 및 폴더 이동\n",
        "!git clone https://github.com/abry-studio/automatic-umbrella.git\n",
        "%cd automatic-umbrella\n",
        "\n",
        "# 3. 숏폼 제작에 필요한 필수 패키지 설치\n",
        "!pip install -r requirements.txt"
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {
        "id": "code-2"
      },
      "outputs": [],
      "source": [
        "import os\n",
        "from google.colab import userdata\n",
        "\n",
        "# 1. Gemini API 키 안전하게 입력받기\n",
        "try:\n",
        "    os.environ[\"GEMINI_API_KEY\"] = userdata.get('GEMINI_API_KEY')\n",
        "    print(\"✅ 코랩 비밀(Secrets) 탭에서 API 키를 성공적으로 불러왔습니다.\")\n",
        "except:\n",
        "    print(\"🔑 아래 네모난 빈칸에 Gemini API 키를 붙여넣고 엔터(Enter)를 치세요:\")\n",
        "    os.environ[\"GEMINI_API_KEY\"] = input()\n",
        "\n",
        "# 2. 웹 서버(Gradio) 실행!\n",
        "print(\"\\n🚀 숏폼 공장 가동 준비 완료! 아래에 나오는 https://어쩌구저쩌구.gradio.live 형태의 링크를 클릭하세요.\")\n",
        "!python app.py"
      ]
    }
  ]
}

with open("Media_Analyzer_Colab.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, ensure_ascii=False, indent=2)

print("Notebook created successfully!")
