(function () {
  const stack = document.getElementById("toast-stack");
  if (!stack) {
    return;
  }

  const noticeMessages = {
    test_created: "Тест успешно создан.",
    test_cloned: "Копия теста успешно создана.",
    test_imported: "Тест успешно импортирован.",
    profile_saved: "Профиль сохранен.",
    photo_uploaded: "Фото профиля обновлено.",
    invite_link_added: "Именованная ссылка добавлена.",
    invite_link_toggled: "Статус ссылки обновлен.",
    psychologist_created: "Психолог успешно создан.",
    psychologist_block_toggled: "Статус блокировки обновлен.",
    psychologist_access_updated: "Дата доступа обновлена.",
  };

  window.uiNotify = function (type, message, timeoutMs) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type || "info"}`;
    toast.setAttribute("role", "status");
    toast.textContent = message;
    stack.appendChild(toast);

    requestAnimationFrame(() => {
      toast.classList.add("is-visible");
    });

    const lifetime = Number.isFinite(timeoutMs) ? timeoutMs : 2500;
    setTimeout(() => {
      toast.classList.remove("is-visible");
      setTimeout(() => toast.remove(), 220);
    }, lifetime);
  };

  window.copyTextWithToast = async function (text, successMessage, errorMessage) {
    try {
      await navigator.clipboard.writeText(text);
      window.uiNotify("success", successMessage || "Скопировано.");
      return true;
    } catch (_error) {
      window.uiNotify("error", errorMessage || "Не удалось скопировать.");
      return false;
    }
  };

  const params = new URLSearchParams(window.location.search);
  const noticeCode = params.get("notice");
  const noticeType = params.get("notice_type") || "success";
  if (noticeCode) {
    const message = noticeMessages[noticeCode] || noticeCode;
    window.uiNotify(noticeType, message);
    params.delete("notice");
    params.delete("notice_type");
    const nextQuery = params.toString();
    const nextUrl =
      window.location.pathname + (nextQuery ? `?${nextQuery}` : "") + window.location.hash;
    window.history.replaceState({}, "", nextUrl);
  }

  document.querySelectorAll("[data-history-back]").forEach((button) => {
    if (button.dataset.bound === "1") {
      return;
    }
    button.dataset.bound = "1";
    button.addEventListener("click", () => {
      const fallback = button.dataset.fallback || "/login";
      if (window.history.length > 1) {
        window.history.back();
        return;
      }
      window.location.href = fallback;
    });
  });
})();
