import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

import requests
import streamlit as st


@dataclass
class Config:
    auth_base: str
    producer_base: str
    ml_base: str


def get_config() -> Config:
    return Config(
        auth_base=st.session_state.get("auth_base", "https://team5.kubepractice.ru/auth"),
        producer_base=st.session_state.get("producer_base", "https://team5.kubepractice.ru/producer"),
        ml_base=st.session_state.get("ml_base", "https://team5.kubepractice.ru/ml"),
    )


def api_request(method: str, url: str, **kwargs) -> Dict[str, Any]:
    headers = kwargs.pop("headers", {})
    headers.setdefault("Content-Type", "application/json")
    try:
        resp = requests.request(method, url, headers=headers, timeout=5, **kwargs)
    except Exception as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc

    try:
        data = resp.json()
    except Exception:
        data = {}

    if not resp.ok:
        detail = data.get("detail") or data.get("message") or resp.text
        raise RuntimeError(f"{resp.status_code}: {detail}")

    return data


def handle_register(cfg: Config) -> None:
    st.subheader("1. Регистрация")
    username = st.text_input("Логин (регистрация)", key="reg_username")
    password = st.text_input("Пароль (регистрация)", type="password", key="reg_password")

    if st.button("Зарегистрироваться"):
        if not username or not password:
            st.error("Введите логин и пароль")
            return
        try:
            api_request(
                "POST",
                f"{cfg.auth_base}/register/",
                json={"username": username, "password": password},
            )
            st.success("Пользователь успешно создан")
        except Exception as exc:
            st.error(str(exc))


def handle_login(cfg: Config) -> None:
    st.subheader("2. Логин")
    username = st.text_input("Логин (логин)", key="login_username")
    password = st.text_input("Пароль (логин)", type="password", key="login_password")

    if st.button("Войти"):
        if not username or not password:
            st.error("Введите логин и пароль")
            return
        try:
            data = api_request(
                "POST",
                f"{cfg.auth_base}/login/",
                json={"username": username, "password": password},
            )
            token = data.get("access_token")
            if not token:
                raise RuntimeError("Token not found in response")
            st.session_state["access_token"] = token
            st.session_state["current_user"] = username
            st.success(f"Вы вошли как {username}")
        except Exception as exc:
            st.session_state["access_token"] = None
            st.session_state["current_user"] = None
            st.error(str(exc))

    if st.session_state.get("current_user"):
        st.info(f"Текущий пользователь: {st.session_state['current_user']}")


def handle_send_review(cfg: Config) -> None:
    st.subheader("3. Отправка отзыва")
    if not st.session_state.get("access_token"):
        st.warning("Сначала войдите, чтобы отправлять отзывы")
        return

    review_text = st.text_area("Текст отзыва", key="review_text", height=120)

    if st.button("Отправить отзыв"):
        if not review_text.strip():
            st.error("Текст отзыва пустой")
            return

        try:
            data = api_request(
                "POST",
                f"{cfg.producer_base}/submit-review/?token={st.session_state['access_token']}",
                json={"review_text": review_text},
            )
            review_id = data.get("review_id")
            if not review_id:
                raise RuntimeError("review_id не вернулся из producer_service")

            st.session_state["last_review_id"] = review_id
            st.success(f"Отзыв отправлен, review_id: {review_id}")
        except Exception as exc:
            st.error(str(exc))


def fetch_review_result(cfg: Config, review_id: str) -> Optional[Dict[str, Any]]:
    token = st.session_state.get("access_token")
    if not token:
        raise RuntimeError("Нет access token")

    try:
        data = api_request(
            "GET",
            f"{cfg.ml_base}/reviews/{review_id}?token={token}",
        )
        return data
    except RuntimeError as exc:
        if "404" in str(exc):
            return None
        raise


def handle_result_view(cfg: Config) -> None:
    st.subheader("4. Результат модели")
    review_id = st.session_state.get("last_review_id")

    if not review_id:
        st.write("Пока нет review_id. Отправьте отзыв выше.")
        return

    if st.button("Получить результат"):
        with st.spinner("Ждём результат от ML-сервиса..."):
            result = None
            for _ in range(10):
                try:
                    result = fetch_review_result(cfg, review_id)
                    if result:
                        break
                except Exception as exc:
                    st.error(str(exc))
                    return
                time.sleep(2)

            if not result:
                st.info("Результат не успел появиться. Попробуйте позже.")
            else:
                st.session_state["last_result"] = result

    result = st.session_state.get("last_result")
    if not result:
        st.write("Результат ещё не загружен.")
        return

    st.markdown("**Последний результат:**")
    st.write(f"**ID:** {result.get('review_id')}")
    st.write(f"**Автор:** {result.get('author') or '-'}")
    st.write(f"**Эмоция:** {result.get('sentiment')}")
    st.write(f"**Оценка:** {result.get('score')}")
    if result.get("reply"):
        st.markdown("**Ответ модели:**")
        st.write(result.get("reply"))
    with st.expander("Текст отзыва"):
        st.write(result.get("review_text"))
    if result.get("created_at"):
        st.write(f"**Создано:** {result.get('created_at')}")


def main() -> None:
    st.set_page_config(page_title="Review Emotion Demo", layout="wide")
    st.title("Review Emotion Demo (Streamlit)")

    cfg = get_config()

    with st.sidebar:
        st.header("Настройки сервисов")
        auth_base = st.text_input("Auth base URL", cfg.auth_base)
        producer_base = st.text_input("Producer base URL", cfg.producer_base)
        ml_base = st.text_input("ML base URL", cfg.ml_base)

        if st.button("Сохранить настройки"):
            st.session_state["auth_base"] = auth_base.strip() or cfg.auth_base
            st.session_state["producer_base"] = producer_base.strip() or cfg.producer_base
            st.session_state["ml_base"] = ml_base.strip() or cfg.ml_base
            st.success("Настройки сохранены. Обновите страницу при необходимости.")

        st.markdown("---")

    handle_register(cfg)
    st.markdown("---")
    handle_login(cfg)
    st.markdown("---")
    handle_send_review(cfg)
    st.markdown("---")
    handle_result_view(cfg)


if __name__ == "__main__":
    main()
