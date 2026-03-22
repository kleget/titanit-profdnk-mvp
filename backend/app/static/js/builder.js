(function () {
  const sectionsNode = document.getElementById("sections");
  const questionsNode = document.getElementById("question-list");
  const formulaNode = document.getElementById("metric-formula-list");
  const manualForm = document.getElementById("manual-builder");
  const addSectionBtn = document.getElementById("add-section");
  const addQuestionBtn = document.getElementById("add-question");
  const addFormulaBtn = document.getElementById("add-metric-formula");
  const clientFieldNode = document.getElementById("client-field-list");
  const addClientFieldBtn = document.getElementById("add-client-field");
  const clientFieldTemplateBtns = [...document.querySelectorAll(".client-field-template")];
  const clientReportBlockNode = document.getElementById("client-report-block-list");
  const psychReportBlockNode = document.getElementById("psych-report-block-list");
  const addClientReportBlockBtn = document.getElementById("add-client-report-block");
  const addPsychReportBlockBtn = document.getElementById("add-psych-report-block");
  const reportTemplatePresetBtns = [...document.querySelectorAll(".report-template-preset")];
  const methodPresetBtns = [...document.querySelectorAll(".method-preset-btn")];
  const formulaPresetBtns = [...document.querySelectorAll(".formula-preset-btn")];
  const draftStatusNode = document.getElementById("builder-draft-status");
  const restoreDraftBtn = document.getElementById("restore-builder-draft");
  const clearDraftBtn = document.getElementById("clear-builder-draft");
  const formulaPreviewRunBtn = document.getElementById("run-formula-preview");
  const formulaPreviewQuestionContextNode = document.getElementById("formula-preview-question-context");
  const formulaPreviewResultsNode = document.getElementById("formula-preview-results");
  const formulaPreviewBaseInputs = [...document.querySelectorAll("[data-formula-base-key]")];

  const DRAFT_STORAGE_KEY = "profdnk_manual_builder_draft_v1";
  const DRAFT_AUTOSAVE_MS = 12000;
  const FORMULA_PREVIEW_BASE_KEYS = new Set([
    "total_score",
    "max_score",
    "score_percent",
    "completion_percent",
    "answered_count",
    "total_questions",
  ]);
  const FORMULA_PREVIEW_ALLOWED_FUNCTIONS = new Set(["min", "max", "abs", "round"]);
  const LOGIC_OPERATORS = [
    { value: "", label: "Без условия" },
    { value: "equals", label: "равно" },
    { value: "not_equals", label: "не равно" },
    { value: "contains", label: "содержит" },
    { value: "not_contains", label: "не содержит" },
    { value: "gt", label: ">" },
    { value: "gte", label: ">=" },
    { value: "lt", label: "<" },
    { value: "lte", label: "<=" },
    { value: "is_true", label: "истина (да/true)" },
    { value: "is_false", label: "ложь (нет/false)" },
    { value: "empty", label: "пусто" },
    { value: "not_empty", label: "не пусто" },
  ];
  const LOGIC_OPERATORS_WITHOUT_VALUE = new Set(["is_true", "is_false", "empty", "not_empty"]);
  const CHOICE_QUESTION_TYPES = new Set(["single_choice", "multiple_choice"]);
  const RANGE_QUESTION_TYPES = new Set(["number", "slider", "rating"]);

  const clientFieldTemplates = {
    school: [
      {
        key: "institution",
        label: "Учебное заведение",
        type: "text",
        required: true,
        placeholder: "Школа/колледж/вуз",
      },
      {
        key: "class_or_group",
        label: "Класс/группа",
        type: "text",
        required: false,
        placeholder: "Например: 10Б или ИВТ-31",
      },
    ],
    career: [
      {
        key: "current_role",
        label: "Текущая деятельность",
        type: "text",
        required: true,
        placeholder: "Учёба, работа, поиск работы",
      },
      {
        key: "experience_years",
        label: "Опыт (лет)",
        type: "number",
        required: false,
        placeholder: "0",
      },
    ],
  };
  const reportBlockCatalog = [
    { key: "profile", label: "Данные клиента" },
    { key: "summary_metrics", label: "Ключевые показатели" },
    { key: "charts", label: "Визуализация метрик" },
    { key: "derived_metrics", label: "Производные метрики" },
    { key: "answers", label: "Ответы по методике" },
  ];
  const reportTemplatePresets = {
    base: {
      client: ["profile", "summary_metrics", "charts", "derived_metrics", "answers"],
      psychologist: ["profile", "summary_metrics", "charts", "derived_metrics", "answers"],
    },
    demo_focus: {
      client: ["profile", "summary_metrics", "derived_metrics"],
      psychologist: ["profile", "summary_metrics", "charts", "derived_metrics", "answers"],
    },
  };
  const methodPresets = {
    school_trajectory: {
      title: "ПрофДНК: школьная траектория",
      description:
        "Стартовая методика для 8-11 классов: интересы, учебная мотивация и готовность к проектному формату.",
      allow_client_report: true,
      required_client_fields: ["full_name", "age"],
      custom_client_fields: [
        {
          key: "institution",
          label: "Школа",
          type: "text",
          required: true,
          placeholder: "Например: Школа №34",
        },
        {
          key: "class_group",
          label: "Класс",
          type: "text",
          required: true,
          placeholder: "Например: 10Б",
        },
      ],
      report_templates: {
        client: ["profile", "summary_metrics", "derived_metrics", "answers"],
        psychologist: ["profile", "summary_metrics", "charts", "derived_metrics", "answers"],
      },
      sections: [
        {
          title: "Профиль ученика",
          questions: [
            {
              text: "Какие предметы вам наиболее интересны и почему?",
              question_type: "textarea",
              required: true,
              weight: 1,
            },
            {
              text: "Оцените текущую учебную мотивацию (1-5)",
              question_type: "rating",
              required: true,
              min_value: 1,
              max_value: 5,
              weight: 1.1,
            },
          ],
        },
        {
          title: "Направления и среда",
          questions: [
            {
              text: "Что для вас важнее при выборе будущего направления?",
              question_type: "single_choice",
              required: true,
              options_json: [
                { label: "Практика и реальные проекты", score: 3 },
                { label: "Академическая база и теория", score: 2 },
                { label: "Баланс теории и практики", score: 2.5 },
              ],
              weight: 1,
            },
            {
              text: "Готовы ли вы посещать дополнительные курсы после школы?",
              question_type: "yes_no",
              required: true,
              weight: 1,
            },
            {
              text: "Комфорт в проектной работе (1-10)",
              question_type: "slider",
              required: true,
              min_value: 1,
              max_value: 10,
              weight: 1.2,
            },
          ],
        },
      ],
      formulas: [
        {
          key: "readiness_index",
          label: "Индекс готовности",
          expression: "round((score_percent + completion_percent) / 2, 2)",
          description: "Сводный индекс вовлеченности в прохождение и общий результат.",
        },
      ],
    },
    college_focus: {
      title: "ПрофДНК: выбор колледжа/вуза",
      description:
        "Методика для абитуриентов: предпочтения по формату обучения, нагрузке и карьерным ожиданиям.",
      allow_client_report: true,
      required_client_fields: ["full_name", "email", "age"],
      custom_client_fields: [
        {
          key: "education_level",
          label: "Текущий уровень образования",
          type: "text",
          required: true,
          placeholder: "9 класс / 11 класс / колледж",
        },
        {
          key: "preferred_city",
          label: "Предпочитаемый город обучения",
          type: "text",
          required: false,
          placeholder: "Например: Ростов-на-Дону",
        },
      ],
      report_templates: {
        client: ["profile", "summary_metrics", "charts", "derived_metrics", "answers"],
        psychologist: ["profile", "summary_metrics", "charts", "derived_metrics", "answers"],
      },
      sections: [
        {
          title: "Образовательный профиль",
          questions: [
            {
              text: "Какие направления обучения вы рассматриваете в первую очередь?",
              question_type: "textarea",
              required: true,
              weight: 1,
            },
            {
              text: "Насколько важна возможность стажировок во время обучения?",
              question_type: "rating",
              required: true,
              min_value: 1,
              max_value: 5,
              weight: 1.1,
            },
          ],
        },
        {
          title: "Формат и нагрузка",
          questions: [
            {
              text: "Какой формат обучения предпочтительнее?",
              question_type: "single_choice",
              required: true,
              options_json: [
                { label: "Очный", score: 3 },
                { label: "Смешанный", score: 2.5 },
                { label: "Дистанционный", score: 2 },
              ],
              weight: 1,
            },
            {
              text: "Какие критерии важны при выборе учебного заведения?",
              question_type: "multiple_choice",
              required: true,
              options_json: [
                { label: "Сильная программа", score: 3 },
                { label: "Стоимость обучения", score: 2 },
                { label: "Репутация и рейтинг", score: 2.5 },
                { label: "Практика и работодатели", score: 3 },
              ],
              weight: 1.1,
            },
            {
              text: "Сколько часов в неделю готовы выделять на самостоятельную учебу?",
              question_type: "number",
              required: true,
              min_value: 1,
              max_value: 60,
              weight: 1,
            },
          ],
        },
      ],
      formulas: [
        {
          key: "discipline_index",
          label: "Индекс дисциплины",
          expression: "round((score_percent * 0.7 + completion_percent * 0.3), 2)",
          description: "Оценка стабильности прохождения и качества ответов.",
        },
      ],
    },
    career_restart: {
      title: "ПрофДНК: карьерный перезапуск",
      description:
        "Методика для взрослых клиентов: оценка мотивации, условий перехода и гибкости к новому формату работы.",
      allow_client_report: true,
      required_client_fields: ["full_name", "email", "phone", "age"],
      custom_client_fields: [
        {
          key: "current_role",
          label: "Текущая роль/сфера",
          type: "text",
          required: true,
          placeholder: "Например: менеджер продаж",
        },
        {
          key: "income_target",
          label: "Целевой доход (руб/мес)",
          type: "number",
          required: false,
          placeholder: "120000",
        },
      ],
      report_templates: {
        client: ["profile", "summary_metrics", "derived_metrics", "answers"],
        psychologist: ["profile", "summary_metrics", "charts", "derived_metrics", "answers"],
      },
      sections: [
        {
          title: "Карьерный контекст",
          questions: [
            {
              text: "Почему вы рассматриваете смену карьерной траектории именно сейчас?",
              question_type: "textarea",
              required: true,
              weight: 1,
            },
            {
              text: "Как быстро готовы стартовать в новой роли?",
              question_type: "single_choice",
              required: true,
              options_json: [
                { label: "В течение 1 месяца", score: 3 },
                { label: "1-3 месяца", score: 2.5 },
                { label: "Позже 3 месяцев", score: 1.5 },
              ],
              weight: 1,
            },
          ],
        },
        {
          title: "Условия перехода",
          questions: [
            {
              text: "Готовы ли временно снизить доход ради смены профессии?",
              question_type: "yes_no",
              required: true,
              weight: 1,
            },
            {
              text: "Что для вас критично в новом месте работы?",
              question_type: "multiple_choice",
              required: true,
              options_json: [
                { label: "Удаленный формат", score: 2 },
                { label: "Стабильная зарплата", score: 3 },
                { label: "Рост и обучение", score: 3 },
                { label: "Гибкий график", score: 2.5 },
              ],
              weight: 1.1,
            },
            {
              text: "Комфорт при высокой неопределенности (1-10)",
              question_type: "slider",
              required: true,
              min_value: 1,
              max_value: 10,
              weight: 1.2,
            },
          ],
        },
      ],
      formulas: [
        {
          key: "transition_readiness",
          label: "Готовность к переходу",
          expression: "round((score_percent + completion_percent) / 2, 2)",
          description: "Общая оценка готовности к смене профессионального трека.",
        },
      ],
    },
  };
  const formulaPresetLibrary = {
    engagement_base: [
      {
        key: "engagement_index",
        label: "Индекс вовлечённости",
        expression: "round((completion_percent * 0.6 + score_percent * 0.4), 2)",
        description: "Показывает, насколько клиент вовлечён и качественно заполняет методику.",
      },
      {
        key: "consistency_index",
        label: "Индекс согласованности",
        expression: "round(max(0, score_percent - (100 - completion_percent)), 2)",
        description: "Оценивает стабильность результата относительно полноты заполнения.",
      },
    ],
    career_readiness: [
      {
        key: "career_readiness",
        label: "Готовность к карьерному шагу",
        expression: "round((score_percent + completion_percent) / 2, 2)",
        description: "Базовый сводный индекс готовности к следующему профессиональному шагу.",
      },
      {
        key: "decision_speed",
        label: "Скорость принятия решения",
        expression: "round((answered_count / max(total_questions, 1)) * 100, 2)",
        description: "Показывает, насколько уверенно клиент прошёл методику без пропусков.",
      },
    ],
    risk_profile: [
      {
        key: "dropout_risk",
        label: "Риск незавершения",
        expression: "round(max(0, 100 - completion_percent), 2)",
        description: "Чем выше значение, тем больше риск потери клиента в воронке прохождения.",
      },
      {
        key: "result_volatility",
        label: "Волатильность результата",
        expression: "round(abs(score_percent - completion_percent), 2)",
        description: "Показывает разброс между качеством ответов и полнотой прохождения.",
      },
    ],
  };

  if (!sectionsNode || !questionsNode || !addSectionBtn || !addQuestionBtn) {
    return;
  }

  let draftDirty = false;

  function notify(type, message, timeoutMs) {
    if (typeof window.uiNotify === "function") {
      window.uiNotify(type, message, timeoutMs);
      return;
    }
    // Резервный вариант, если общий слой уведомлений недоступен.
    console.log(`[${type}] ${message}`);
  }

  function removeValidationError(input) {
    input.classList.remove("is-invalid");
    const parent = input.parentElement;
    if (!parent) {
      return;
    }
    const error = parent.querySelector(".field-error");
    if (error) {
      error.remove();
    }
  }

  function setValidationError(input, message) {
    input.classList.add("is-invalid");
    const parent = input.parentElement;
    if (!parent) {
      return;
    }
    let error = parent.querySelector(".field-error");
    if (!error) {
      error = document.createElement("small");
      error.className = "field-error";
      parent.appendChild(error);
    }
    error.textContent = message;
  }

  function clearValidationErrors() {
    document.querySelectorAll(".is-invalid").forEach((node) => node.classList.remove("is-invalid"));
    document.querySelectorAll(".field-error").forEach((node) => node.remove());
  }

  function createEmptyState(message, actionText, onAction) {
    const box = document.createElement("div");
    box.className = "empty-state";
    const text = document.createElement("p");
    text.textContent = message;
    box.appendChild(text);
    if (actionText && typeof onAction === "function") {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn small ghost";
      button.textContent = actionText;
      button.addEventListener("click", onAction);
      box.appendChild(button);
    }
    return box;
  }

  function sectionOptions() {
    return [...sectionsNode.querySelectorAll("input[name='section_titles[]']")]
      .map((input) => input.value.trim())
      .filter(Boolean);
  }

  function buildCopyTitle(baseTitle, existingTitles) {
    const cleanBase = String(baseTitle || "").trim() || "Секция";
    const pool = new Set(existingTitles.map((item) => item.toLowerCase()));
    let candidate = `${cleanBase} (копия)`;
    let counter = 2;
    while (pool.has(candidate.toLowerCase())) {
      candidate = `${cleanBase} (копия ${counter})`;
      counter += 1;
    }
    return candidate;
  }

  function buildFormulaCopyKey(baseKey, existingKeys) {
    const cleanBase =
      String(baseKey || "")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_]+/g, "_")
        .replace(/^_+|_+$/g, "") || "metric";
    const pool = new Set(existingKeys.map((item) => item.toLowerCase()));
    let candidate = `${cleanBase}_copy`;
    let counter = 2;
    while (pool.has(candidate)) {
      candidate = `${cleanBase}_copy_${counter}`;
      counter += 1;
    }
    return candidate;
  }

  function normalizeBuilderKey(source, fallback) {
    const prepared = String(source || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_]+/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_+|_+$/g, "");
    return prepared || fallback;
  }

  function parseFormulaIdentifiers(expression) {
    const matches = String(expression || "").match(/[A-Za-z_][A-Za-z0-9_]*/g) || [];
    return [...new Set(matches)];
  }

  function buildLogicOperatorOptions(selected = "") {
    return LOGIC_OPERATORS.map((operator) => {
      const selectedAttr = operator.value === selected ? "selected" : "";
      return `<option value="${operator.value}" ${selectedAttr}>${operator.label}</option>`;
    }).join("");
  }

  function buildQuestionConditionKeys() {
    const seen = new Set();
    const keys = [];
    [...questionsNode.querySelectorAll(".question-item")].forEach((item, index) => {
      const keyInput = item.querySelector("input[name='q_key[]']");
      const textInput = item.querySelector("input[name='q_text[]']");
      const key = normalizeBuilderKey(
        (keyInput?.value || "").trim() || (textInput?.value || "").trim(),
        `question_${index + 1}`
      );
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      keys.push(key);
    });
    return keys;
  }

  function syncLogicKeyReferences() {
    const datalistId = "builder-question-keys";
    let datalist = document.getElementById(datalistId);
    if (!datalist) {
      datalist = document.createElement("datalist");
      datalist.id = datalistId;
      manualForm?.appendChild(datalist);
    }

    const keys = buildQuestionConditionKeys();
    datalist.innerHTML = keys.map((key) => `<option value="${escapeHtml(key)}"></option>`).join("");

    [...document.querySelectorAll("input[name='section_if_key[]'], input[name='q_if_key[]']")].forEach(
      (input) => {
        input.setAttribute("list", datalistId);
      }
    );

    [...questionsNode.querySelectorAll(".question-item")].forEach((item, index) => {
      const keyInput = item.querySelector("input[name='q_key[]']");
      const textInput = item.querySelector("input[name='q_text[]']");
      const keyPreview = item.querySelector("[data-question-key-preview]");
      const normalized = normalizeBuilderKey(
        (keyInput?.value || "").trim() || (textInput?.value || "").trim(),
        `question_${index + 1}`
      );
      if (keyPreview) {
        keyPreview.textContent = `Ключ вопроса: ${normalized}`;
      }
    });
  }

  function syncLogicValueState(container) {
    if (!container) {
      return;
    }
    const operatorInput = container.querySelector("[data-logic-operator]");
    const valueInput = container.querySelector("[data-logic-value]");
    if (!(operatorInput instanceof HTMLSelectElement) || !(valueInput instanceof HTMLInputElement)) {
      return;
    }
    const operator = operatorInput.value.trim().toLowerCase();
    const noValue = LOGIC_OPERATORS_WITHOUT_VALUE.has(operator) || !operator;
    valueInput.disabled = noValue;
    if (noValue) {
      valueInput.value = "";
      valueInput.placeholder = "Значение не требуется";
    } else {
      valueInput.placeholder = "Значение условия";
    }
  }

  function readQuestionPayload(box) {
    const sectionSelect = box.querySelector("select[name='q_section[]']");
    const typeSelect = box.querySelector("select[name='q_type[]']");
    const requiredSelect = box.querySelector("select[name='q_required[]']");
    const keyInput = box.querySelector("input[name='q_key[]']");
    const textInput = box.querySelector("input[name='q_text[]']");
    const optionsInput = box.querySelector("input[name='q_options[]']");
    const minInput = box.querySelector("input[name='q_min[]']");
    const maxInput = box.querySelector("input[name='q_max[]']");
    const weightInput = box.querySelector("input[name='q_weight[]']");
    const ifKeyInput = box.querySelector("input[name='q_if_key[]']");
    const ifOperatorInput = box.querySelector("select[name='q_if_operator[]']");
    const ifValueInput = box.querySelector("input[name='q_if_value[]']");

    return {
      section: sectionSelect?.value || "",
      question_type: typeSelect?.value || "text",
      required: (requiredSelect?.value || "true") === "true",
      key: keyInput?.value || "",
      text: textInput?.value || "",
      options_flat: optionsInput?.value || "",
      min_value: minInput?.value || "",
      max_value: maxInput?.value || "",
      weight: weightInput?.value || "1",
      if_key: ifKeyInput?.value || "",
      if_operator: ifOperatorInput?.value || "",
      if_value: ifValueInput?.value || "",
    };
  }

  function readSectionPayload(box) {
    return {
      title: box.querySelector("input[name='section_titles[]']")?.value || "",
      if_key: box.querySelector("input[name='section_if_key[]']")?.value || "",
      if_operator: box.querySelector("select[name='section_if_operator[]']")?.value || "",
      if_value: box.querySelector("input[name='section_if_value[]']")?.value || "",
    };
  }

  function readFormulaPayload(box) {
    return {
      key: box.querySelector("input[name='metric_key[]']")?.value || "",
      label: box.querySelector("input[name='metric_label[]']")?.value || "",
      expression: box.querySelector("input[name='metric_expression[]']")?.value || "",
      description: box.querySelector("input[name='metric_description[]']")?.value || "",
    };
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function collectFormulaPreviewFormulas() {
    return [...(formulaNode?.querySelectorAll(".question-item") || [])]
      .map((item, index) => {
        const payload = readFormulaPayload(item);
        const expression = String(payload.expression || "").trim();
        const key = normalizeBuilderKey(payload.key || payload.label || "", `metric_${index + 1}`);
        const touched =
          expression ||
          String(payload.key || "").trim() ||
          String(payload.label || "").trim() ||
          String(payload.description || "").trim();
        if (!touched) {
          return null;
        }
        return {
          key,
          label: String(payload.label || key).trim(),
          expression,
        };
      })
      .filter(Boolean);
  }

  function collectFormulaPreviewQuestionKeys() {
    const keys = [];
    const seen = new Set();
    [...questionsNode.querySelectorAll(".question-item")].forEach((item, index) => {
      const textInput = item.querySelector("input[name='q_text[]']");
      const keyInput = item.querySelector("input[name='q_key[]']");
      const key = normalizeBuilderKey(
        (keyInput?.value || "").trim() || (textInput?.value || "").trim(),
        `question_${index + 1}`
      );
      if (!seen.has(key)) {
        seen.add(key);
        keys.push(key);
      }
    });
    return keys;
  }

  function syncFormulaPreviewContextInputs() {
    if (!formulaPreviewQuestionContextNode) {
      return;
    }

    const currentValues = new Map(
      [...formulaPreviewQuestionContextNode.querySelectorAll("input[data-formula-context-key]")]
        .map((input) => [input.dataset.formulaContextKey || "", input.value])
        .filter(([key]) => Boolean(key))
    );
    const formulas = collectFormulaPreviewFormulas();
    const questionKeys = collectFormulaPreviewQuestionKeys();
    const formulaKeys = new Set(formulas.map((formula) => formula.key));
    const requiredKeys = [];
    const seenRequired = new Set();

    function appendKey(rawKey) {
      const key = String(rawKey || "").trim();
      if (!key || seenRequired.has(key)) {
        return;
      }
      seenRequired.add(key);
      requiredKeys.push(key);
    }

    questionKeys.forEach(appendKey);
    formulas.forEach((formula) => {
      parseFormulaIdentifiers(formula.expression).forEach((identifier) => {
        if (
          FORMULA_PREVIEW_BASE_KEYS.has(identifier) ||
          FORMULA_PREVIEW_ALLOWED_FUNCTIONS.has(identifier) ||
          formulaKeys.has(identifier)
        ) {
          return;
        }
        appendKey(identifier);
      });
    });

    formulaPreviewQuestionContextNode.innerHTML = "";
    if (!requiredKeys.length) {
      const muted = document.createElement("p");
      muted.className = "muted";
      muted.textContent = "Дополнительные переменные не требуются: используются только базовые метрики.";
      formulaPreviewQuestionContextNode.appendChild(muted);
      return;
    }

    requiredKeys.forEach((key) => {
      const label = document.createElement("label");
      label.textContent = key;
      const input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.placeholder = "0";
      input.dataset.formulaContextKey = key;
      input.value = currentValues.get(key) || "";
      label.appendChild(input);
      formulaPreviewQuestionContextNode.appendChild(label);
    });
  }

  function parsePreviewNumber(rawValue) {
    const text = String(rawValue || "")
      .trim()
      .replace(",", ".");
    if (!text) {
      return 0;
    }
    const value = Number(text);
    if (!Number.isFinite(value)) {
      return null;
    }
    return value;
  }

  function collectFormulaPreviewContext() {
    const context = {};
    const issues = [];

    formulaPreviewBaseInputs.forEach((input) => {
      const key = input.dataset.formulaBaseKey;
      if (!key) {
        return;
      }
      const parsed = parsePreviewNumber(input.value);
      if (parsed === null) {
        issues.push(`Поле ${key} должно быть числом.`);
        return;
      }
      context[key] = parsed;
    });

    if (formulaPreviewQuestionContextNode) {
      formulaPreviewQuestionContextNode
        .querySelectorAll("input[data-formula-context-key]")
        .forEach((input) => {
          const key = input.dataset.formulaContextKey;
          if (!key) {
            return;
          }
          const parsed = parsePreviewNumber(input.value);
          if (parsed === null) {
            issues.push(`Поле ${key} должно быть числом.`);
            return;
          }
          context[key] = parsed;
        });
    }

    return { context, issues };
  }

  function collectStrictFormulaIssues() {
    const issues = [];
    const formulaItems = [...(formulaNode?.querySelectorAll(".question-item") || [])];
    const formulaResolvedKeys = formulaItems.map((item, index) => {
      const keyInput = item.querySelector("input[name='metric_key[]']");
      const labelInput = item.querySelector("input[name='metric_label[]']");
      return normalizeBuilderKey(
        (keyInput?.value || "").trim() || (labelInput?.value || "").trim(),
        `metric_${index + 1}`
      );
    });
    const formulaKeyPosition = new Map(formulaResolvedKeys.map((key, index) => [key, index]));
    const availableVariables = new Set([
      ...FORMULA_PREVIEW_BASE_KEYS,
      ...collectFormulaPreviewQuestionKeys(),
    ]);

    formulaItems.forEach((item, index) => {
      const expressionInput = item.querySelector("input[name='metric_expression[]']");
      const expression = String(expressionInput?.value || "").trim();
      if (!expression) {
        return;
      }
      const dependencies = parseFormulaIdentifiers(expression).filter(
        (identifier) => !FORMULA_PREVIEW_ALLOWED_FUNCTIONS.has(identifier)
      );
      for (const dependency of dependencies) {
        if (availableVariables.has(dependency)) {
          continue;
        }
        const dependencyPosition = formulaKeyPosition.get(dependency);
        if (dependencyPosition === undefined) {
          issues.push({
            input: expressionInput,
            message: `Формула #${index + 1}: неизвестная переменная '${dependency}'. Используйте ключи вопросов.`,
          });
          break;
        }
        if (dependencyPosition >= index) {
          issues.push({
            input: expressionInput,
            message: `Формула #${index + 1}: переменная '${dependency}' объявлена ниже по списку формул.`,
          });
          break;
        }
      }
      availableVariables.add(formulaResolvedKeys[index]);
    });
    return issues;
  }

  function renderFormulaPreviewResults(results) {
    if (!formulaPreviewResultsNode) {
      return;
    }
    formulaPreviewResultsNode.innerHTML = "";

    if (!Array.isArray(results) || !results.length) {
      formulaPreviewResultsNode.appendChild(
        createEmptyState("Нет результатов предпросмотра. Запусти проверку формул.", "", null)
      );
      return;
    }

    results.forEach((item, index) => {
      const card = document.createElement("div");
      const isOk = item?.status === "ok";
      card.className = `formula-preview-result ${isOk ? "is-ok" : "is-error"}`;

      const head = document.createElement("div");
      head.className = "formula-preview-head";

      const title = document.createElement("strong");
      title.textContent = String(item?.label || item?.key || `Формула #${index + 1}`);
      head.appendChild(title);

      const badge = document.createElement("span");
      badge.className = `status-badge ${isOk ? "status-active" : "status-exhausted"}`;
      badge.textContent = isOk ? "OK" : "Ошибка";
      head.appendChild(badge);
      card.appendChild(head);

      const expression = document.createElement("p");
      expression.className = "formula-preview-expression";
      expression.innerHTML = `<code>${escapeHtml(item?.expression || "")}</code>`;
      card.appendChild(expression);

      const valueLine = document.createElement("p");
      valueLine.className = "formula-preview-value";
      valueLine.textContent = isOk
        ? `Результат: ${String(item?.value ?? "-")}`
        : `Причина: ${String(item?.error || "Не удалось вычислить формулу.")}`;
      card.appendChild(valueLine);

      formulaPreviewResultsNode.appendChild(card);
    });
  }

  async function runFormulaPreview() {
    if (!formulaPreviewResultsNode) {
      return;
    }
    syncFormulaPreviewContextInputs();

    const formulas = collectFormulaPreviewFormulas();
    if (!formulas.length) {
      notify("info", "Добавь хотя бы одну формулу для проверки.");
      renderFormulaPreviewResults([]);
      return;
    }
    if (formulas.some((formula) => !formula.expression)) {
      notify("error", "Для заполненных строк формул укажи выражение.");
      return;
    }

    const strictIssues = collectStrictFormulaIssues();
    if (strictIssues.length) {
      const firstIssue = strictIssues[0];
      if (firstIssue?.input) {
        setValidationError(firstIssue.input, firstIssue.message);
      }
      notify("error", firstIssue?.message || "Формулы содержат ошибки.");
      formulaPreviewResultsNode.innerHTML = "";
      formulaPreviewResultsNode.appendChild(
        createEmptyState(firstIssue?.message || "Формулы содержат ошибки.", "", null)
      );
      return;
    }

    const { context, issues } = collectFormulaPreviewContext();
    if (issues.length) {
      notify("error", issues[0]);
      return;
    }

    const csrfToken = manualForm?.querySelector("input[name='csrf_token']")?.value || "";
    if (!csrfToken) {
      notify("error", "Не найден CSRF-токен. Обнови страницу и повтори попытку.");
      return;
    }

    if (formulaPreviewRunBtn) {
      formulaPreviewRunBtn.disabled = true;
    }
    formulaPreviewResultsNode.innerHTML = "";
    formulaPreviewResultsNode.appendChild(
      createEmptyState("Вычисляю формулы на тестовых данных...", "", null)
    );

    try {
      const response = await fetch("/api/formulas/preview", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({ formulas, context }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail =
          typeof payload?.detail === "string"
            ? payload.detail
            : "Не удалось выполнить предпросмотр формул.";
        notify("error", detail);
        formulaPreviewResultsNode.innerHTML = "";
        formulaPreviewResultsNode.appendChild(createEmptyState(detail, "", null));
        return;
      }
      const results = Array.isArray(payload?.results) ? payload.results : [];
      renderFormulaPreviewResults(results);
      const hasErrors = results.some((item) => item?.status !== "ok");
      if (hasErrors) {
        notify("info", "Проверка выполнена: в части формул есть ошибки.");
      } else {
        notify("success", "Проверка выполнена: формулы рассчитываются корректно.");
      }
    } catch (_error) {
      notify("error", "Ошибка сети при проверке формул. Повтори попытку.");
      formulaPreviewResultsNode.innerHTML = "";
      formulaPreviewResultsNode.appendChild(
        createEmptyState("Ошибка сети при проверке формул. Повтори попытку.", "", null)
      );
    } finally {
      if (formulaPreviewRunBtn) {
        formulaPreviewRunBtn.disabled = false;
      }
    }
  }

  function createSectionInput(value = "") {
    const sectionPayload =
      typeof value === "object" && value !== null
        ? {
            title: String(value.title || ""),
            if_key: String(value.if_key || ""),
            if_operator: String(value.if_operator || ""),
            if_value: String(value.if_value || ""),
          }
        : {
            title: String(value || ""),
            if_key: "",
            if_operator: "",
            if_value: "",
          };
    const wrapper = document.createElement("div");
    wrapper.className = "question-item section-item builder-section-card";
    const input = document.createElement("input");
    input.name = "section_titles[]";
    input.placeholder = "Название секции";
    input.required = true;
    input.value = sectionPayload.title;
    const ifKeyInput = document.createElement("input");
    ifKeyInput.name = "section_if_key[]";
    ifKeyInput.placeholder = "Ключ вопроса (например: remote_ready)";

    const ifOperatorSelect = document.createElement("select");
    ifOperatorSelect.name = "section_if_operator[]";
    ifOperatorSelect.dataset.logicOperator = "1";
    ifOperatorSelect.innerHTML = buildLogicOperatorOptions("");

    const ifValueInput = document.createElement("input");
    ifValueInput.name = "section_if_value[]";
    ifValueInput.dataset.logicValue = "1";
    ifValueInput.placeholder = "Значение условия";

    ifKeyInput.value = sectionPayload.if_key;
    ifOperatorSelect.value = sectionPayload.if_operator;
    ifValueInput.value = sectionPayload.if_value;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn small ghost";
    remove.textContent = "Удалить";
    remove.addEventListener("click", () => {
      wrapper.remove();
      syncQuestionSections();
      syncEmptyStates();
      syncLogicKeyReferences();
      markDraftDirty();
    });
    input.addEventListener("input", () => {
      syncQuestionSections();
      syncLogicKeyReferences();
    });

    const logicRow = document.createElement("div");
    logicRow.className = "inline-form logic-inline builder-section-logic";

    const keyLabel = document.createElement("label");
    keyLabel.textContent = "Показать секцию, если ключ";
    keyLabel.appendChild(ifKeyInput);

    const operatorLabel = document.createElement("label");
    operatorLabel.textContent = "Оператор";
    operatorLabel.appendChild(ifOperatorSelect);

    const valueLabel = document.createElement("label");
    valueLabel.textContent = "Значение";
    valueLabel.appendChild(ifValueInput);

    logicRow.append(keyLabel, operatorLabel, valueLabel);

    const helper = document.createElement("p");
    helper.className = "muted";
    helper.textContent =
      "Условие секции можно привязать только к вопросам из предыдущих секций.";

    const duplicate = document.createElement("button");
    duplicate.type = "button";
    duplicate.className = "btn small ghost";
    duplicate.textContent = "Дублировать";
    duplicate.addEventListener("click", () => {
      const sourceTitle = input.value.trim();
      const copyTitle = buildCopyTitle(sourceTitle || "Секция", sectionOptions());
      const duplicateSection = createSectionInput({
        title: copyTitle,
        if_key: ifKeyInput.value.trim(),
        if_operator: ifOperatorSelect.value,
        if_value: ifValueInput.value.trim(),
      });
      wrapper.parentNode.insertBefore(duplicateSection, wrapper.nextSibling);

      const sourceQuestions = [...questionsNode.querySelectorAll(".question-item")]
        .map((item) => readQuestionPayload(item))
        .filter((payload) => payload.section === sourceTitle);

      sourceQuestions.forEach((payload) => {
        const duplicatedQuestion = createQuestionItem({
          ...payload,
          section: copyTitle,
        });
        questionsNode.appendChild(duplicatedQuestion);
      });

      syncQuestionSections();
      syncEmptyStates();
      syncLogicKeyReferences();
      markDraftDirty();
      notify("success", "Секция и её вопросы продублированы.");
    });

    const headRow = document.createElement("div");
    headRow.className = "inline-form builder-section-head";
    const titleLabel = document.createElement("label");
    titleLabel.textContent = "Название секции";
    titleLabel.appendChild(input);
    const actionRow = document.createElement("div");
    actionRow.className = "actions-row";
    actionRow.append(duplicate, remove);
    headRow.append(titleLabel, actionRow);

    ifOperatorSelect.addEventListener("change", () => {
      syncLogicValueState(wrapper);
      markDraftDirty();
    });
    ifKeyInput.addEventListener("input", markDraftDirty);
    ifValueInput.addEventListener("input", markDraftDirty);
    syncLogicValueState(wrapper);

    wrapper.append(headRow, logicRow, helper);
    return wrapper;
  }

  function toNumericScore(rawValue, fallback = 1) {
    const text = String(rawValue ?? "").trim().replace(",", ".");
    if (!text) {
      return fallback;
    }
    const parsed = Number(text);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function scoreToText(score) {
    const numeric = Number(score);
    if (!Number.isFinite(numeric)) {
      return "1";
    }
    return String(numeric);
  }

  function createChoiceOptionRow(questionBox, payload = {}) {
    const row = document.createElement("div");
    row.className = "builder-option-row";
    row.innerHTML = `
      <label>
        Вариант
        <input type="text" class="builder-option-label" placeholder="Например: Стабильность">
      </label>
      <label>
        Балл
        <input type="number" class="builder-option-score" step="0.1" value="1">
      </label>
      <button type="button" class="btn small ghost builder-option-remove">Удалить</button>
    `;

    const labelInput = row.querySelector(".builder-option-label");
    const scoreInput = row.querySelector(".builder-option-score");
    const removeBtn = row.querySelector(".builder-option-remove");

    if (labelInput) {
      labelInput.value = String(payload.label || "");
      labelInput.addEventListener("input", () => {
        syncChoiceOptionsInput(questionBox);
        markDraftDirty();
      });
    }
    if (scoreInput) {
      scoreInput.value = scoreToText(toNumericScore(payload.score, 1));
      scoreInput.addEventListener("input", () => {
        syncChoiceOptionsInput(questionBox);
        markDraftDirty();
      });
    }
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        row.remove();
        syncChoiceOptionsInput(questionBox);
        markDraftDirty();
      });
    }

    return row;
  }

  function syncChoiceOptionsInput(questionBox) {
    const hiddenOptionsInput = questionBox.querySelector("input[name='q_options[]']");
    const rows = [...questionBox.querySelectorAll(".builder-option-row")];
    const serialized = rows
      .map((row) => {
        const label = String(row.querySelector(".builder-option-label")?.value || "").trim();
        if (!label) {
          return "";
        }
        const scoreValue = toNumericScore(row.querySelector(".builder-option-score")?.value, 1);
        return `${label}:${scoreValue}`;
      })
      .filter(Boolean)
      .join(", ");

    if (hiddenOptionsInput) {
      hiddenOptionsInput.value = serialized;
    }

    const emptyHint = questionBox.querySelector("[data-options-empty]");
    if (emptyHint instanceof HTMLElement) {
      emptyHint.hidden = rows.length > 0;
    }
  }

  function renderChoiceOptions(questionBox, flatValue = "") {
    const listNode = questionBox.querySelector("[data-options-list]");
    if (!(listNode instanceof HTMLElement)) {
      return;
    }
    listNode.innerHTML = "";
    const parsed = parseChoiceOptions(flatValue);
    const seed = parsed.length ? parsed : [{ label: "", score: 1 }, { label: "", score: 1 }];
    seed.forEach((item) => {
      listNode.appendChild(createChoiceOptionRow(questionBox, item));
    });
    syncChoiceOptionsInput(questionBox);
  }

  function syncQuestionTypeUI(questionBox, applyDefaults = false) {
    const typeSelect = questionBox.querySelector("select[name='q_type[]']");
    const typeValue = typeSelect?.value || "text";
    const optionsEditor = questionBox.querySelector("[data-options-editor]");
    const rangeRow = questionBox.querySelector("[data-range-row]");
    const rangeHint = questionBox.querySelector("[data-range-hint]");
    const minInput = questionBox.querySelector("input[name='q_min[]']");
    const maxInput = questionBox.querySelector("input[name='q_max[]']");
    const optionsList = questionBox.querySelector("[data-options-list]");
    const optionsInput = questionBox.querySelector("input[name='q_options[]']");

    const isChoiceType = CHOICE_QUESTION_TYPES.has(typeValue);
    const isRangeType = RANGE_QUESTION_TYPES.has(typeValue);

    if (optionsEditor instanceof HTMLElement) {
      optionsEditor.hidden = !isChoiceType;
      if (isChoiceType && optionsList instanceof HTMLElement && !optionsList.children.length) {
        renderChoiceOptions(questionBox, optionsInput?.value || "");
      }
    }

    if (rangeRow instanceof HTMLElement) {
      rangeRow.hidden = !isRangeType;
    }

    if (rangeHint instanceof HTMLElement) {
      if (!isRangeType) {
        rangeHint.hidden = true;
      } else {
        rangeHint.hidden = false;
        if (typeValue === "slider") {
          rangeHint.textContent = "Диапазон для шкалы слайдера (например, 0-10).";
        } else if (typeValue === "rating") {
          rangeHint.textContent = "Диапазон оценок для радио-кнопок (например, 1-5).";
        } else {
          rangeHint.textContent = "Диапазон допустимых числовых значений для ответа.";
        }
      }
    }

    if (!isRangeType && applyDefaults) {
      if (minInput instanceof HTMLInputElement) {
        minInput.value = "";
      }
      if (maxInput instanceof HTMLInputElement) {
        maxInput.value = "";
      }
    }
    if (isRangeType && applyDefaults) {
      if (typeValue === "slider") {
        if (minInput instanceof HTMLInputElement && !String(minInput.value).trim()) {
          minInput.value = "0";
        }
        if (maxInput instanceof HTMLInputElement && !String(maxInput.value).trim()) {
          maxInput.value = "10";
        }
      } else if (typeValue === "rating") {
        if (minInput instanceof HTMLInputElement && !String(minInput.value).trim()) {
          minInput.value = "1";
        }
        if (maxInput instanceof HTMLInputElement && !String(maxInput.value).trim()) {
          maxInput.value = "5";
        }
      }
    }
  }

  function createQuestionItem(payload = {}) {
    const box = document.createElement("div");
    box.className = "question-item builder-question-card";
    box.innerHTML = `
      <div class="inline-form builder-question-row builder-question-row--meta">
        <label>Секция
          <select name="q_section[]"></select>
        </label>
        <label>Тип
          <select name="q_type[]">
            <option value="text">Короткий текст</option>
            <option value="textarea">Большой текст</option>
            <option value="single_choice">Один вариант</option>
            <option value="multiple_choice">Несколько вариантов</option>
            <option value="yes_no">Да / Нет</option>
            <option value="number">Число</option>
            <option value="slider">Слайдер</option>
            <option value="datetime">Дата и время</option>
            <option value="rating">Оценка</option>
          </select>
        </label>
        <label>Обязательный
          <select name="q_required[]">
            <option value="true">Да</option>
            <option value="false">Нет</option>
          </select>
        </label>
      </div>

      <label class="builder-question-main-field">Текст вопроса
        <input name="q_text[]" required placeholder="Введите формулировку вопроса">
      </label>

      <label>Ключ вопроса (опционально)
        <input name="q_key[]" placeholder="remote_ready">
      </label>
      <p class="field-hint">Ключ нужен для ветвлений и формул. Если оставить пустым, система создаст его автоматически.</p>
      <p class="muted question-key-preview" data-question-key-preview></p>

      <div class="builder-options-editor" data-options-editor hidden>
        <div class="builder-options-head">
          <strong>Варианты ответов</strong>
          <button type="button" class="btn small ghost add-option-row">+ Вариант</button>
        </div>
        <p class="field-hint">
          Заполняйте вариант и балл в отдельных полях. Формат <code>Текст:балл</code> формируется автоматически.
        </p>
        <input type="hidden" name="q_options[]">
        <div class="builder-options-list" data-options-list></div>
        <p class="field-hint" data-options-empty>Пока нет вариантов. Для выбора обычно нужно минимум 2.</p>
      </div>

      <div class="inline-form builder-question-row builder-question-row--range" data-range-row hidden>
        <label>Минимум
          <input type="number" step="any" name="q_min[]">
        </label>
        <label>Максимум
          <input type="number" step="any" name="q_max[]">
        </label>
      </div>
      <p class="field-hint" data-range-hint hidden></p>

      <details class="collapse-panel builder-question-advanced">
        <summary>Расширенные настройки (вес и ветвления)</summary>
        <div class="builder-question-row builder-question-row--weight">
          <label>Вес вопроса
            <input type="number" step="0.1" name="q_weight[]" value="1">
          </label>
        </div>
        <p class="field-hint">Вес влияет на вклад вопроса в итоговый балл. Базовое значение: 1.</p>
        <div class="inline-form logic-inline builder-question-row builder-question-row--logic">
          <label>Показать вопрос, если ключ
            <input name="q_if_key[]" placeholder="Ключ вопроса (например: remote_ready)">
          </label>
          <label>Оператор
            <select name="q_if_operator[]" data-logic-operator>
              ${buildLogicOperatorOptions("")}
            </select>
          </label>
          <label>Значение
            <input name="q_if_value[]" data-logic-value placeholder="Значение условия">
          </label>
        </div>
        <p class="field-hint">Ветвление: вопрос будет показан только при выполнении условия.</p>
      </details>

      <div class="actions-row builder-question-actions">
        <button type="button" class="btn small ghost duplicate-question">Дублировать вопрос</button>
        <button type="button" class="btn small ghost remove-question">Удалить вопрос</button>
      </div>
    `;

    const sectionSelect = box.querySelector("select[name='q_section[]']");
    const typeSelect = box.querySelector("select[name='q_type[]']");
    const requiredSelect = box.querySelector("select[name='q_required[]']");
    const keyInput = box.querySelector("input[name='q_key[]']");
    const textInput = box.querySelector("input[name='q_text[]']");
    const optionsInput = box.querySelector("input[name='q_options[]']");
    const minInput = box.querySelector("input[name='q_min[]']");
    const maxInput = box.querySelector("input[name='q_max[]']");
    const weightInput = box.querySelector("input[name='q_weight[]']");
    const ifKeyInput = box.querySelector("input[name='q_if_key[]']");
    const ifOperatorSelect = box.querySelector("select[name='q_if_operator[]']");
    const ifValueInput = box.querySelector("input[name='q_if_value[]']");
    const addOptionBtn = box.querySelector(".add-option-row");
    const optionsList = box.querySelector("[data-options-list]");

    const visibilityCondition =
      payload.visibility_condition && typeof payload.visibility_condition === "object"
        ? payload.visibility_condition
        : null;

    if (typeSelect && payload.question_type) {
      typeSelect.value = payload.question_type;
    }
    if (requiredSelect) {
      const requiredValue = typeof payload.required === "boolean" ? payload.required : true;
      requiredSelect.value = requiredValue ? "true" : "false";
    }
    if (keyInput && payload.key) {
      keyInput.value = payload.key;
    }
    if (textInput && payload.text) {
      textInput.value = payload.text;
    }
    if (optionsInput && payload.options_flat) {
      optionsInput.value = payload.options_flat;
    }
    if (minInput) {
      minInput.value = payload.min_value || "";
    }
    if (maxInput) {
      maxInput.value = payload.max_value || "";
    }
    if (weightInput && payload.weight) {
      weightInput.value = payload.weight;
    }
    if (sectionSelect && payload.section) {
      sectionSelect.dataset.preferredSection = payload.section;
    }
    if (ifKeyInput) {
      ifKeyInput.value = payload.if_key || visibilityCondition?.question_key || "";
    }
    if (ifOperatorSelect) {
      ifOperatorSelect.value = payload.if_operator || visibilityCondition?.operator || "";
    }
    if (ifValueInput) {
      ifValueInput.value = payload.if_value || visibilityCondition?.value || "";
    }

    if (optionsList instanceof HTMLElement) {
      renderChoiceOptions(box, optionsInput?.value || "");
    }
    if (addOptionBtn) {
      addOptionBtn.addEventListener("click", () => {
        if (!(optionsList instanceof HTMLElement)) {
          return;
        }
        optionsList.appendChild(createChoiceOptionRow(box, { label: "", score: 1 }));
        syncChoiceOptionsInput(box);
        markDraftDirty();
      });
    }

    ifOperatorSelect?.addEventListener("change", () => {
      syncLogicValueState(box);
      markDraftDirty();
    });
    if (typeSelect) {
      typeSelect.addEventListener("change", () => {
        syncQuestionTypeUI(box, true);
        markDraftDirty();
      });
    }
    syncLogicValueState(box);
    syncQuestionTypeUI(box, true);

    const duplicateBtn = box.querySelector(".duplicate-question");
    duplicateBtn.addEventListener("click", () => {
      const duplicatePayload = readQuestionPayload(box);
      const duplicateItem = createQuestionItem(duplicatePayload);
      box.parentNode.insertBefore(duplicateItem, box.nextSibling);
      syncQuestionSections();
      syncEmptyStates();
      syncFormulaPreviewContextInputs();
      syncLogicKeyReferences();
      markDraftDirty();
      notify("success", "Вопрос продублирован.");
    });

    const removeBtn = box.querySelector(".remove-question");
    removeBtn.addEventListener("click", () => {
      box.remove();
      syncEmptyStates();
      syncFormulaPreviewContextInputs();
      syncLogicKeyReferences();
      markDraftDirty();
    });
    keyInput?.addEventListener("input", () => {
      syncFormulaPreviewContextInputs();
      syncLogicKeyReferences();
      markDraftDirty();
    });
    textInput?.addEventListener("input", () => {
      syncFormulaPreviewContextInputs();
      syncLogicKeyReferences();
      markDraftDirty();
    });
    minInput?.addEventListener("input", markDraftDirty);
    maxInput?.addEventListener("input", markDraftDirty);
    weightInput?.addEventListener("input", markDraftDirty);
    ifKeyInput?.addEventListener("input", markDraftDirty);
    ifValueInput?.addEventListener("input", markDraftDirty);
    syncLogicKeyReferences();
    return box;
  }

  function createFormulaItem(payload = {}) {
    const box = document.createElement("div");
    box.className = "question-item";
    box.innerHTML = `
      <div class="inline-form">
        <label>Ключ метрики
          <input name="metric_key[]" placeholder="adaptability_index">
        </label>
        <label>Название
          <input name="metric_label[]" placeholder="Индекс адаптивности">
        </label>
      </div>
      <label>Формула
        <input name="metric_expression[]" placeholder="round((digital_skill + stress_level) / 2, 2)">
      </label>
      <label>Описание
        <input name="metric_description[]" placeholder="Что показывает метрика">
      </label>
      <div class="actions-row">
        <button type="button" class="btn small ghost duplicate-formula">Дублировать формулу</button>
        <button type="button" class="btn small ghost remove-formula">Удалить формулу</button>
      </div>
    `;

    const keyInput = box.querySelector("input[name='metric_key[]']");
    const labelInput = box.querySelector("input[name='metric_label[]']");
    const expressionInput = box.querySelector("input[name='metric_expression[]']");
    const descriptionInput = box.querySelector("input[name='metric_description[]']");
    if (keyInput && payload.key) {
      keyInput.value = payload.key;
    }
    if (labelInput && payload.label) {
      labelInput.value = payload.label;
    }
    if (expressionInput && payload.expression) {
      expressionInput.value = payload.expression;
    }
    if (descriptionInput && payload.description) {
      descriptionInput.value = payload.description;
    }

    box.querySelector(".duplicate-formula").addEventListener("click", () => {
      const duplicatePayload = readFormulaPayload(box);
      duplicatePayload.key = buildFormulaCopyKey(
        duplicatePayload.key || "metric",
        [...formulaNode.querySelectorAll("input[name='metric_key[]']")]
          .map((input) => input.value.trim())
          .filter(Boolean)
      );
      const duplicateItem = createFormulaItem(duplicatePayload);
      box.parentNode.insertBefore(duplicateItem, box.nextSibling);
      syncEmptyStates();
      syncFormulaPreviewContextInputs();
      markDraftDirty();
      notify("success", "Формула продублирована.");
    });

    const removeBtn = box.querySelector(".remove-formula");
    removeBtn.addEventListener("click", () => {
      box.remove();
      syncEmptyStates();
      syncFormulaPreviewContextInputs();
      markDraftDirty();
    });
    return box;
  }

  function createClientFieldItem(payload = {}) {
    const box = document.createElement("div");
    box.className = "question-item";
    box.innerHTML = `
      <div class="inline-form">
        <label>Ключ
          <input name="cf_key[]" placeholder="city" value="${payload.key || ""}">
        </label>
        <label>Название поля
          <input name="cf_label[]" required placeholder="Город проживания" value="${payload.label || ""}">
        </label>
        <label>Тип
          <select name="cf_type[]">
            <option value="text">Короткий текст</option>
            <option value="textarea">Большой текст</option>
            <option value="number">Число</option>
            <option value="date">Дата</option>
            <option value="email">Email</option>
            <option value="phone">Телефон</option>
          </select>
        </label>
        <label>Обязательное
          <select name="cf_required[]">
            <option value="false">Нет</option>
            <option value="true">Да</option>
          </select>
        </label>
      </div>
      <label>Плейсхолдер
        <input name="cf_placeholder[]" placeholder="Подсказка в поле" value="${payload.placeholder || ""}">
      </label>
      <button type="button" class="btn small ghost remove-client-field">Удалить поле</button>
    `;
    box.querySelector("select[name='cf_type[]']").value = payload.type || "text";
    box.querySelector("select[name='cf_required[]']").value = payload.required ? "true" : "false";
    box.querySelector(".remove-client-field").addEventListener("click", () => {
      box.remove();
      syncEmptyStates();
      markDraftDirty();
    });
    return box;
  }

  function readClientFieldPayload(box) {
    return {
      key: box.querySelector("input[name='cf_key[]']")?.value || "",
      label: box.querySelector("input[name='cf_label[]']")?.value || "",
      type: box.querySelector("select[name='cf_type[]']")?.value || "text",
      required: (box.querySelector("select[name='cf_required[]']")?.value || "false") === "true",
      placeholder: box.querySelector("input[name='cf_placeholder[]']")?.value || "",
    };
  }

  function applyClientFieldTemplate(templateKey) {
    if (!clientFieldNode) {
      return;
    }
    const template = clientFieldTemplates[templateKey];
    if (!template) {
      return;
    }
    const existingKeys = new Set(
      [...clientFieldNode.querySelectorAll("input[name='cf_key[]']")]
        .map((input) => input.value.trim().toLowerCase())
        .filter(Boolean)
    );
    template.forEach((field) => {
      if (field.key && existingKeys.has(field.key.toLowerCase())) {
        return;
      }
      clientFieldNode.appendChild(createClientFieldItem(field));
    });
    syncEmptyStates();
    markDraftDirty();
    notify("info", "Добавлен шаблон полей клиента.");
  }

  function createReportBlockItem(fieldName, selectedKey = "summary_metrics") {
    const box = document.createElement("div");
    box.className = "inline-form report-block-item";
    box.innerHTML = `
      <label>
        Блок
        <select name="${fieldName}"></select>
      </label>
      <div class="actions-row">
        <button type="button" class="btn small ghost move-up">Вверх</button>
        <button type="button" class="btn small ghost move-down">Вниз</button>
        <button type="button" class="btn small ghost remove-report-block">Удалить</button>
      </div>
    `;
    const select = box.querySelector("select");
    reportBlockCatalog.forEach((block) => {
      const option = document.createElement("option");
      option.value = block.key;
      option.textContent = block.label;
      select.appendChild(option);
    });
    if ([...select.options].some((option) => option.value === selectedKey)) {
      select.value = selectedKey;
    }

    box.querySelector(".remove-report-block").addEventListener("click", () => {
      box.remove();
      syncEmptyStates();
      markDraftDirty();
    });
    box.querySelector(".move-up").addEventListener("click", () => {
      const prev = box.previousElementSibling;
      if (prev) {
        box.parentNode.insertBefore(box, prev);
        markDraftDirty();
      }
    });
    box.querySelector(".move-down").addEventListener("click", () => {
      const next = box.nextElementSibling;
      if (next) {
        box.parentNode.insertBefore(next, box);
        markDraftDirty();
      }
    });
    return box;
  }

  function fillReportBlockList(node, fieldName, keys) {
    if (!node) {
      return;
    }
    node.innerHTML = "";
    keys.forEach((key) => {
      node.appendChild(createReportBlockItem(fieldName, key));
    });
  }

  function ensureReportBlockDefaults() {
    if (!clientReportBlockNode || !psychReportBlockNode) {
      return;
    }
    if (!clientReportBlockNode.children.length) {
      fillReportBlockList(clientReportBlockNode, "rt_client[]", reportTemplatePresets.base.client);
    }
    if (!psychReportBlockNode.children.length) {
      fillReportBlockList(
        psychReportBlockNode,
        "rt_psychologist[]",
        reportTemplatePresets.base.psychologist
      );
    }
  }

  function applyReportTemplatePreset(key) {
    const preset = reportTemplatePresets[key];
    if (!preset) {
      return;
    }
    fillReportBlockList(clientReportBlockNode, "rt_client[]", preset.client);
    fillReportBlockList(psychReportBlockNode, "rt_psychologist[]", preset.psychologist);
    syncEmptyStates();
    markDraftDirty();
    notify("info", "Применён пресет шаблона отчётов.");
  }

  function optionsToFlatValue(options) {
    if (!Array.isArray(options) || !options.length) {
      return "";
    }
    return options
      .map((item) => {
        const label = String(item?.label || "").trim();
        if (!label) {
          return "";
        }
        const score = Number(item?.score);
        if (Number.isFinite(score)) {
          return `${label}:${score}`;
        }
        return label;
      })
      .filter(Boolean)
      .join(", ");
  }

  function applyBuiltinRequiredFields(fields) {
    if (!manualForm) {
      return;
    }
    const required = new Set(
      (Array.isArray(fields) ? fields : [])
        .map((item) => String(item).trim().toLowerCase())
        .filter(Boolean)
    );
    manualForm
      .querySelectorAll("input[name='required_client_fields']")
      .forEach((input) => {
        input.checked = required.has(input.value);
      });
  }

  function applyMethodPreset(key) {
    const preset = methodPresets[key];
    if (!preset || !manualForm) {
      return;
    }

    const titleInput = manualForm.querySelector("input[name='title']");
    const descriptionInput = manualForm.querySelector("textarea[name='description']");
    const reportSelect = manualForm.querySelector("select[name='allow_client_report']");
    if (titleInput) {
      titleInput.value = preset.title || "";
    }
    if (descriptionInput) {
      descriptionInput.value = preset.description || "";
    }
    if (reportSelect) {
      reportSelect.value = preset.allow_client_report ? "true" : "false";
    }
    applyBuiltinRequiredFields(preset.required_client_fields || []);

    if (clientFieldNode) {
      clientFieldNode.innerHTML = "";
      (preset.custom_client_fields || []).forEach((field) => {
        clientFieldNode.appendChild(createClientFieldItem(field));
      });
    }

    const reportTemplates = preset.report_templates || reportTemplatePresets.base;
    fillReportBlockList(clientReportBlockNode, "rt_client[]", reportTemplates.client || []);
    fillReportBlockList(
      psychReportBlockNode,
      "rt_psychologist[]",
      reportTemplates.psychologist || []
    );

    sectionsNode.innerHTML = "";
    (preset.sections || []).forEach((section) => {
      sectionsNode.appendChild(
        createSectionInput({
          title: section.title || "Секция",
          if_key: section.visibility_condition?.question_key || "",
          if_operator: section.visibility_condition?.operator || "",
          if_value: section.visibility_condition?.value || "",
        })
      );
    });
    syncQuestionSections();

    questionsNode.innerHTML = "";
    (preset.sections || []).forEach((section) => {
      (section.questions || []).forEach((question) => {
        const item = createQuestionItem({
          section: section.title || "Общая секция",
          question_type: question.question_type || "text",
          required: question.required !== false,
          key: question.key || "",
          text: question.text || "",
          options_flat: optionsToFlatValue(question.options_json),
          min_value:
            typeof question.min_value === "number" && Number.isFinite(question.min_value)
              ? String(question.min_value)
              : "",
          max_value:
            typeof question.max_value === "number" && Number.isFinite(question.max_value)
              ? String(question.max_value)
              : "",
          weight:
            typeof question.weight === "number" && Number.isFinite(question.weight)
              ? String(question.weight)
              : "1",
          visibility_condition: question.visibility_condition || null,
        });
        questionsNode.appendChild(item);
      });
    });

    if (formulaNode) {
      formulaNode.innerHTML = "";
      (preset.formulas || []).forEach((formula) => {
        const item = createFormulaItem();
        const keyInput = item.querySelector("input[name='metric_key[]']");
        const labelInput = item.querySelector("input[name='metric_label[]']");
        const expressionInput = item.querySelector("input[name='metric_expression[]']");
        const descriptionField = item.querySelector("input[name='metric_description[]']");
        if (keyInput) {
          keyInput.value = formula.key || "";
        }
        if (labelInput) {
          labelInput.value = formula.label || "";
        }
        if (expressionInput) {
          expressionInput.value = formula.expression || "";
        }
        if (descriptionField) {
          descriptionField.value = formula.description || "";
        }
        formulaNode.appendChild(item);
      });
    }

    clearValidationErrors();
    syncQuestionSections();
    syncEmptyStates();
    syncFormulaPreviewContextInputs();
    syncLogicKeyReferences();
    markDraftDirty();
    notify("success", "Пресет применён. Проверьте детали и создайте тест.");
  }

  function applyFormulaPreset(key) {
    const preset = formulaPresetLibrary[key];
    if (!preset || !formulaNode) {
      return;
    }
    const existingKeys = new Set(
      [...formulaNode.querySelectorAll("input[name='metric_key[]']")]
        .map((input) => input.value.trim().toLowerCase())
        .filter(Boolean)
    );

    preset.forEach((formula) => {
      const baseKey = String(formula.key || "metric").trim().toLowerCase();
      let nextKey = baseKey || "metric";
      let suffix = 2;
      while (existingKeys.has(nextKey)) {
        nextKey = `${baseKey}_${suffix}`;
        suffix += 1;
      }
      existingKeys.add(nextKey);
      formulaNode.appendChild(
        createFormulaItem({
          ...formula,
          key: nextKey,
        })
      );
    });

    syncEmptyStates();
    syncFormulaPreviewContextInputs();
    markDraftDirty();
    notify("success", "Пресет формул добавлен в методику.");
  }

  function draftStatus(text, tone = "muted") {
    if (!draftStatusNode) {
      return;
    }
    draftStatusNode.textContent = text;
    draftStatusNode.dataset.tone = tone;
  }

  function formatDateTime(dateValue) {
    const date = new Date(dateValue);
    if (Number.isNaN(date.getTime())) {
      return "неизвестно";
    }
    return date.toLocaleString();
  }

  function collectBuilderDraft() {
    return {
      version: 1,
      saved_at: new Date().toISOString(),
      title: manualForm?.querySelector("input[name='title']")?.value || "",
      description: manualForm?.querySelector("textarea[name='description']")?.value || "",
      allow_client_report:
        manualForm?.querySelector("select[name='allow_client_report']")?.value || "true",
      required_client_fields: [...(manualForm?.querySelectorAll("input[name='required_client_fields']") || [])]
        .filter((input) => input.checked)
        .map((input) => input.value),
      sections: [...sectionsNode.querySelectorAll(".section-item")].map((item) =>
        readSectionPayload(item)
      ),
      questions: [...questionsNode.querySelectorAll(".question-item")].map((item) =>
        readQuestionPayload(item)
      ),
      formulas: [...(formulaNode?.querySelectorAll(".question-item") || [])].map((item) =>
        readFormulaPayload(item)
      ),
      custom_client_fields: [...(clientFieldNode?.querySelectorAll(".question-item") || [])].map((item) =>
        readClientFieldPayload(item)
      ),
      report_templates: {
        client: [...(clientReportBlockNode?.querySelectorAll("select[name='rt_client[]']") || [])].map(
          (select) => select.value
        ),
        psychologist: [
          ...(psychReportBlockNode?.querySelectorAll("select[name='rt_psychologist[]']") || []),
        ].map((select) => select.value),
      },
    };
  }

  function readStoredDraft() {
    try {
      const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") {
        return null;
      }
      return parsed;
    } catch (_error) {
      return null;
    }
  }

  function refreshDraftButtons() {
    const hasDraft = Boolean(readStoredDraft());
    if (restoreDraftBtn) {
      restoreDraftBtn.disabled = !hasDraft;
    }
    if (clearDraftBtn) {
      clearDraftBtn.disabled = !hasDraft;
    }
  }

  function saveDraftNow(silent = false) {
    try {
      const payload = collectBuilderDraft();
      localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(payload));
      draftDirty = false;
      if (!silent) {
        draftStatus(`Черновик сохранён: ${formatDateTime(payload.saved_at)}`, "success");
      }
      refreshDraftButtons();
    } catch (_error) {
      if (!silent) {
        draftStatus("Не удалось сохранить черновик (ограничение браузера).", "error");
      }
    }
  }

  function clearStoredDraft(showNotice = true) {
    try {
      localStorage.removeItem(DRAFT_STORAGE_KEY);
    } catch (_error) {
      // storage may be unavailable; ignore
    }
    refreshDraftButtons();
    if (showNotice) {
      draftStatus("Черновик очищен.", "muted");
      notify("info", "Сохранённый черновик удалён.");
    }
  }

  function applyBuilderDraft(draft) {
    if (!draft || typeof draft !== "object") {
      return false;
    }

    const titleInput = manualForm?.querySelector("input[name='title']");
    const descriptionInput = manualForm?.querySelector("textarea[name='description']");
    const reportSelect = manualForm?.querySelector("select[name='allow_client_report']");
    if (titleInput) {
      titleInput.value = draft.title || "";
    }
    if (descriptionInput) {
      descriptionInput.value = draft.description || "";
    }
    if (reportSelect) {
      reportSelect.value = draft.allow_client_report || "true";
    }
    applyBuiltinRequiredFields(draft.required_client_fields || []);

    const sectionPayloads = Array.isArray(draft.sections) ? draft.sections : [];
    sectionsNode.innerHTML = "";
    sectionPayloads.forEach((sectionPayload) => {
      if (typeof sectionPayload === "string") {
        sectionsNode.appendChild(createSectionInput(sectionPayload || ""));
        return;
      }
      sectionsNode.appendChild(
        createSectionInput({
          title: sectionPayload?.title || "",
          if_key: sectionPayload?.if_key || "",
          if_operator: sectionPayload?.if_operator || "",
          if_value: sectionPayload?.if_value || "",
        })
      );
    });

    questionsNode.innerHTML = "";
    (draft.questions || []).forEach((questionPayload) => {
      questionsNode.appendChild(createQuestionItem(questionPayload));
    });

    if (formulaNode) {
      formulaNode.innerHTML = "";
      (draft.formulas || []).forEach((formulaPayload) => {
        formulaNode.appendChild(createFormulaItem(formulaPayload));
      });
    }

    if (clientFieldNode) {
      clientFieldNode.innerHTML = "";
      (draft.custom_client_fields || []).forEach((fieldPayload) => {
        clientFieldNode.appendChild(createClientFieldItem(fieldPayload));
      });
    }

    fillReportBlockList(
      clientReportBlockNode,
      "rt_client[]",
      draft.report_templates?.client || reportTemplatePresets.base.client
    );
    fillReportBlockList(
      psychReportBlockNode,
      "rt_psychologist[]",
      draft.report_templates?.psychologist || reportTemplatePresets.base.psychologist
    );

    clearValidationErrors();
    syncQuestionSections();
    syncEmptyStates();
    syncFormulaPreviewContextInputs();
    syncLogicKeyReferences();
    return true;
  }

  function initDraftControls() {
    const stored = readStoredDraft();
    if (stored?.saved_at) {
      draftStatus(`Найден черновик: ${formatDateTime(stored.saved_at)}`, "info");
    } else {
      draftStatus("Черновик: не сохранён", "muted");
    }
    refreshDraftButtons();

    if (restoreDraftBtn) {
      restoreDraftBtn.addEventListener("click", () => {
        const draft = readStoredDraft();
        if (!draft) {
          notify("info", "Сохранённый черновик не найден.");
          refreshDraftButtons();
          return;
        }
        const restored = applyBuilderDraft(draft);
        if (restored) {
          draftDirty = false;
          draftStatus(`Черновик восстановлен: ${formatDateTime(draft.saved_at)}`, "success");
          notify("success", "Черновик конструктора восстановлен.");
        }
      });
    }

    if (clearDraftBtn) {
      clearDraftBtn.addEventListener("click", () => {
        clearStoredDraft(true);
      });
    }

    setInterval(() => {
      if (draftDirty) {
        saveDraftNow(true);
        const latest = readStoredDraft();
        if (latest?.saved_at) {
          draftStatus(`Черновик сохранён: ${formatDateTime(latest.saved_at)}`, "success");
        }
      }
    }, DRAFT_AUTOSAVE_MS);
  }

  function markDraftDirty() {
    draftDirty = true;
    draftStatus("Есть несохранённые изменения. Автосохранение через 12 сек.", "warning");
  }

  function syncEmptyState(node, message, actionText, actionHandler) {
    if (!node) {
      return;
    }
    [...node.querySelectorAll(":scope > .empty-state")].forEach((item) => item.remove());
    const dataItems = [...node.children].filter((item) => !item.classList.contains("empty-state"));
    if (dataItems.length === 0) {
      node.appendChild(createEmptyState(message, actionText, actionHandler));
    }
  }

  function syncEmptyStates() {
    syncEmptyState(
      sectionsNode,
      "Пока нет секций. Добавь хотя бы одну, чтобы сгруппировать вопросы.",
      "Добавить секцию",
      () => {
        sectionsNode.appendChild(createSectionInput());
        syncQuestionSections();
        syncEmptyStates();
      }
    );
    syncEmptyState(
      questionsNode,
      "Пока нет вопросов. Добавь вопрос, чтобы создать рабочую методику.",
      "Добавить вопрос",
      () => {
        questionsNode.appendChild(createQuestionItem());
        syncQuestionSections();
        syncEmptyStates();
      }
    );
    syncEmptyState(
      formulaNode,
      "Формулы пока не добавлены. Можно оставить пусто или добавить свои метрики.",
      "Добавить формулу",
      () => {
        formulaNode.appendChild(createFormulaItem());
        syncEmptyStates();
      }
    );
    syncEmptyState(
      clientFieldNode,
      "Дополнительных полей клиента пока нет.",
      "Добавить поле",
      () => {
        clientFieldNode.appendChild(createClientFieldItem());
        syncEmptyStates();
      }
    );
    syncEmptyState(
      clientReportBlockNode,
      "Список блоков клиентского отчёта пуст.",
      "Добавить блок",
      () => {
        clientReportBlockNode.appendChild(createReportBlockItem("rt_client[]"));
        syncEmptyStates();
      }
    );
    syncEmptyState(
      psychReportBlockNode,
      "Список блоков профессионального отчёта пуст.",
      "Добавить блок",
      () => {
        psychReportBlockNode.appendChild(createReportBlockItem("rt_psychologist[]"));
        syncEmptyStates();
      }
    );
  }

  function syncQuestionSections() {
    const values = sectionOptions();
    questionsNode.querySelectorAll("select[name='q_section[]']").forEach((select) => {
      const current = select.dataset.preferredSection || select.value;
      select.innerHTML = "";
      (values.length ? values : ["Общая секция"]).forEach((item) => {
        const option = document.createElement("option");
        option.value = item;
        option.textContent = item;
        select.appendChild(option);
      });
      if ([...select.options].some((opt) => opt.value === current)) {
        select.value = current;
      }
      delete select.dataset.preferredSection;
    });
    syncLogicKeyReferences();
  }

  addSectionBtn.addEventListener("click", () => {
    sectionsNode.appendChild(createSectionInput());
    syncQuestionSections();
    syncEmptyStates();
    syncFormulaPreviewContextInputs();
    markDraftDirty();
  });

  addQuestionBtn.addEventListener("click", () => {
    questionsNode.appendChild(createQuestionItem());
    syncQuestionSections();
    syncEmptyStates();
    syncFormulaPreviewContextInputs();
    markDraftDirty();
  });

  if (addFormulaBtn && formulaNode) {
    addFormulaBtn.addEventListener("click", () => {
      formulaNode.appendChild(createFormulaItem());
      syncEmptyStates();
      syncFormulaPreviewContextInputs();
      markDraftDirty();
    });
  }

  if (addClientFieldBtn && clientFieldNode) {
    addClientFieldBtn.addEventListener("click", () => {
      clientFieldNode.appendChild(createClientFieldItem());
      syncEmptyStates();
      markDraftDirty();
    });
  }
  clientFieldTemplateBtns.forEach((button) => {
    button.addEventListener("click", () => {
      applyClientFieldTemplate(button.dataset.template);
    });
  });
  if (addClientReportBlockBtn && clientReportBlockNode) {
    addClientReportBlockBtn.addEventListener("click", () => {
      clientReportBlockNode.appendChild(createReportBlockItem("rt_client[]"));
      syncEmptyStates();
      markDraftDirty();
    });
  }
  if (addPsychReportBlockBtn && psychReportBlockNode) {
    addPsychReportBlockBtn.addEventListener("click", () => {
      psychReportBlockNode.appendChild(createReportBlockItem("rt_psychologist[]"));
      syncEmptyStates();
      markDraftDirty();
    });
  }
  reportTemplatePresetBtns.forEach((button) => {
    button.addEventListener("click", () => {
      applyReportTemplatePreset(button.dataset.template);
    });
  });
  methodPresetBtns.forEach((button) => {
    button.addEventListener("click", () => {
      applyMethodPreset(button.dataset.template || "");
    });
  });
  formulaPresetBtns.forEach((button) => {
    button.addEventListener("click", () => {
      applyFormulaPreset(button.dataset.template || "");
    });
  });
  if (formulaPreviewRunBtn) {
    formulaPreviewRunBtn.addEventListener("click", () => {
      runFormulaPreview();
    });
  }
  if (questionsNode) {
    questionsNode.addEventListener("input", (event) => {
      const target = event.target;
      if (target instanceof HTMLInputElement && target.name === "q_text[]") {
        syncFormulaPreviewContextInputs();
      }
    });
  }
  if (formulaNode) {
    formulaNode.addEventListener("input", (event) => {
      const target = event.target;
      if (
        target instanceof HTMLInputElement &&
        ["metric_key[]", "metric_label[]", "metric_expression[]"].includes(target.name)
      ) {
        syncFormulaPreviewContextInputs();
      }
    });
  }

  function parseChoiceOptions(value) {
    return String(value || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
      .map((item, index) => {
        if (!item.includes(":")) {
          return {
            label: item,
            score: 1,
            value: normalizeBuilderKey(item, `option_${index + 1}`),
          };
        }
        const [rawLabel, rawScore] = item.split(/:(?=[^:]+$)/);
        const label = String(rawLabel || "").trim();
        const score = toNumericScore(rawScore, 1);
        return {
          label,
          score,
          value: normalizeBuilderKey(label, `option_${index + 1}`),
        };
      })
      .filter((item) => item.label);
  }

  function parseLogicCondition(keyInput, operatorInput, valueInput, label, issues) {
    const questionKey = String(keyInput?.value || "").trim();
    const operator = String(operatorInput?.value || "").trim().toLowerCase();
    const conditionValue = String(valueInput?.value || "").trim();
    const hasAny = Boolean(questionKey || operator || conditionValue);
    if (!hasAny) {
      return null;
    }
    if (!questionKey) {
      if (keyInput) {
        setValidationError(keyInput, "Укажи ключ вопроса для условия.");
      }
      issues.push(`${label}: укажи ключ вопроса в условии.`);
      return null;
    }
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(questionKey)) {
      if (keyInput) {
        setValidationError(keyInput, "Ключ условия: только латиница, цифры и _.");
      }
      issues.push(`${label}: некорректный ключ в условии.`);
      return null;
    }
    if (!LOGIC_OPERATORS.some((item) => item.value === operator && item.value !== "")) {
      if (operatorInput) {
        setValidationError(operatorInput, "Выбери оператор условия.");
      }
      issues.push(`${label}: выбери оператор условия.`);
      return null;
    }
    if (!LOGIC_OPERATORS_WITHOUT_VALUE.has(operator) && !conditionValue) {
      if (valueInput) {
        setValidationError(valueInput, "Для выбранного оператора нужно значение.");
      }
      issues.push(`${label}: заполни значение условия.`);
      return null;
    }
    return {
      question_key: questionKey,
      operator,
      value: conditionValue,
    };
  }

  function validateReportBlocks(container, fieldName, labelPrefix, issues) {
    const selects = [...(container?.querySelectorAll(`select[name='${fieldName}']`) || [])];
    if (!selects.length) {
      issues.push(`${labelPrefix}: добавь хотя бы один блок.`);
      return;
    }
    const seen = new Set();
    selects.forEach((select) => {
      const value = select.value;
      if (seen.has(value)) {
        setValidationError(select, "Блок уже добавлен. Удалите дубликат.");
        issues.push(`${labelPrefix}: есть дубликаты блоков.`);
      }
      seen.add(value);
    });
  }

  function validateBuilderForm() {
    clearValidationErrors();
    const issues = [];

    const titleInput = manualForm?.querySelector("input[name='title']");
    if (titleInput && titleInput.value.trim().length < 5) {
      setValidationError(titleInput, "Минимум 5 символов.");
      issues.push("Укажи понятное название теста (не короче 5 символов).");
    }

    const sectionItems = [...sectionsNode.querySelectorAll(".section-item")];
    if (!sectionItems.length) {
      issues.push("Добавь хотя бы одну секцию.");
    }
    const sectionTitlesInOrder = [];
    const sectionConditionsInOrder = [];
    const seenSectionTitles = new Set();
    sectionItems.forEach((item, index) => {
      const titleInput = item.querySelector("input[name='section_titles[]']");
      const ifKeyInput = item.querySelector("input[name='section_if_key[]']");
      const ifOperatorInput = item.querySelector("select[name='section_if_operator[]']");
      const ifValueInput = item.querySelector("input[name='section_if_value[]']");
      const title = titleInput?.value?.trim() || "";
      sectionTitlesInOrder.push(title);
      if (!title) {
        if (titleInput) {
          setValidationError(titleInput, "Название секции обязательно.");
        }
        issues.push(`Секция #${index + 1}: пустое название.`);
      } else {
        if (seenSectionTitles.has(title.toLowerCase())) {
          if (titleInput) {
            setValidationError(titleInput, "Названия секций должны быть уникальными.");
          }
          issues.push(`Секция #${index + 1}: дублирующееся название.`);
        }
        seenSectionTitles.add(title.toLowerCase());
      }
      sectionConditionsInOrder.push(
        parseLogicCondition(
          ifKeyInput,
          ifOperatorInput,
          ifValueInput,
          `Секция #${index + 1}`,
          issues
        )
      );
    });

    const questionItems = [...questionsNode.querySelectorAll(".question-item")];
    if (!questionItems.length) {
      issues.push("Добавь минимум один вопрос.");
    }
    const questionResolvedKeys = [];
    const questionConditionsInOrder = [];
    const seenQuestionKeys = new Set();
    const questionSectionTitles = [];
    questionItems.forEach((item, index) => {
      const qText = item.querySelector("input[name='q_text[]']");
      const qKeyInput = item.querySelector("input[name='q_key[]']");
      const qType = item.querySelector("select[name='q_type[]']");
      const qOptions = item.querySelector("input[name='q_options[]']");
      const qMin = item.querySelector("input[name='q_min[]']");
      const qMax = item.querySelector("input[name='q_max[]']");
      const qSection = item.querySelector("select[name='q_section[]']");
      const qIfKeyInput = item.querySelector("input[name='q_if_key[]']");
      const qIfOperatorInput = item.querySelector("select[name='q_if_operator[]']");
      const qIfValueInput = item.querySelector("input[name='q_if_value[]']");

      if (!qText || !qText.value.trim()) {
        if (qText) {
          setValidationError(qText, "Текст вопроса обязателен.");
        }
        issues.push(`Вопрос #${index + 1}: заполни формулировку.`);
      }

      const resolvedKey = normalizeBuilderKey(
        (qKeyInput?.value || "").trim() || (qText?.value || "").trim(),
        `question_${index + 1}`
      );
      if (seenQuestionKeys.has(resolvedKey)) {
        if (qKeyInput || qText) {
          setValidationError(qKeyInput || qText, "Ключ вопроса должен быть уникальным.");
        }
        issues.push(`Вопрос #${index + 1}: дублирующийся ключ '${resolvedKey}'.`);
      }
      seenQuestionKeys.add(resolvedKey);
      questionResolvedKeys.push(resolvedKey);
      questionSectionTitles.push((qSection?.value || "").trim() || "Общая секция");
      questionConditionsInOrder.push(
        parseLogicCondition(
          qIfKeyInput,
          qIfOperatorInput,
          qIfValueInput,
          `Вопрос #${index + 1}`,
          issues
        )
      );

      const typeValue = qType?.value || "text";
      if (typeValue === "single_choice" || typeValue === "multiple_choice") {
        const options = parseChoiceOptions(qOptions?.value || "");
        if (options.length < 2) {
          const optionLabelInput = item.querySelector(".builder-option-label");
          if (optionLabelInput) {
            setValidationError(optionLabelInput, "Добавьте минимум 2 варианта ответа.");
          } else if (qOptions) {
            setValidationError(qOptions, "Для вопросов с выбором нужно минимум 2 варианта.");
          }
          issues.push(`Вопрос #${index + 1}: для выбора нужно минимум 2 варианта.`);
        }
      }

      const minRaw = qMin?.value?.trim() || "";
      const maxRaw = qMax?.value?.trim() || "";
      if (minRaw && maxRaw && Number(minRaw) > Number(maxRaw)) {
        if (qMax) {
          setValidationError(qMax, "Максимум должен быть не меньше минимума.");
        }
        issues.push(`Вопрос #${index + 1}: проверь диапазон min/max.`);
      }
    });

    // Проверяем зависимости ветвлений по порядку секций и вопросов.
    const knownQuestionKeys = new Set();
    sectionTitlesInOrder.forEach((sectionTitle, sectionIndex) => {
      if (!sectionTitle) {
        return;
      }
      const sectionCondition = sectionConditionsInOrder[sectionIndex];
      if (sectionCondition && !knownQuestionKeys.has(sectionCondition.question_key)) {
        const sectionItem = sectionItems[sectionIndex];
        const ifKeyInput = sectionItem?.querySelector("input[name='section_if_key[]']");
        if (ifKeyInput) {
          setValidationError(ifKeyInput, "Можно ссылаться только на вопросы из предыдущих секций.");
        }
        issues.push(
          `Секция #${sectionIndex + 1}: условие ссылается на '${sectionCondition.question_key}', который ещё не определён.`
        );
      }

      questionItems.forEach((item, questionIndex) => {
        if (questionSectionTitles[questionIndex] !== sectionTitle) {
          return;
        }
        const questionCondition = questionConditionsInOrder[questionIndex];
        if (questionCondition && !knownQuestionKeys.has(questionCondition.question_key)) {
          const ifKeyInput = item.querySelector("input[name='q_if_key[]']");
          if (ifKeyInput) {
            setValidationError(ifKeyInput, "Ссылка на вопрос ниже по порядку недопустима.");
          }
          issues.push(
            `Вопрос #${questionIndex + 1}: условие ссылается на '${questionCondition.question_key}', который объявлен ниже или отсутствует.`
          );
        }
        knownQuestionKeys.add(questionResolvedKeys[questionIndex]);
      });
    });

    const customKeyInputs = [...(clientFieldNode?.querySelectorAll("input[name='cf_key[]']") || [])];
    const seenCustomKeys = new Set();
    customKeyInputs.forEach((input) => {
      const key = input.value.trim().toLowerCase();
      if (!key) {
        return;
      }
      if (seenCustomKeys.has(key)) {
        setValidationError(input, "Ключ должен быть уникальным.");
        issues.push("В дополнительных полях есть дублирующиеся ключи.");
      }
      seenCustomKeys.add(key);
    });

    const formulaItems = [...(formulaNode?.querySelectorAll(".question-item") || [])];
    const formulaResolvedKeys = [];
    const seenFormulaKeys = new Set();
    formulaItems.forEach((item, index) => {
      const keyInput = item.querySelector("input[name='metric_key[]']");
      const labelInput = item.querySelector("input[name='metric_label[]']");
      const resolvedKey = normalizeBuilderKey(
        (keyInput?.value || "").trim() || (labelInput?.value || "").trim(),
        `metric_${index + 1}`
      );
      formulaResolvedKeys.push(resolvedKey);
      if (seenFormulaKeys.has(resolvedKey)) {
        if (keyInput || labelInput) {
          setValidationError(keyInput || labelInput, "Ключ формулы должен быть уникальным.");
        }
        issues.push(`Формула #${index + 1}: дублирующийся ключ ${resolvedKey}.`);
      }
      seenFormulaKeys.add(resolvedKey);
    });

    const formulaKeyPosition = new Map(
      formulaResolvedKeys.map((key, index) => [key, index])
    );
    const availableFormulaVariables = new Set([
      ...FORMULA_PREVIEW_BASE_KEYS,
      ...collectFormulaPreviewQuestionKeys(),
    ]);
    formulaItems.forEach((item, index) => {
      const expressionInput = item.querySelector("input[name='metric_expression[]']");
      const keyInput = item.querySelector("input[name='metric_key[]']");
      const labelInput = item.querySelector("input[name='metric_label[]']");
      const descriptionInput = item.querySelector("input[name='metric_description[]']");
      const expression = expressionInput?.value?.trim() || "";
      const touched = [keyInput, labelInput, descriptionInput].some(
        (input) => (input?.value || "").trim() !== ""
      );
      if (touched && !expression && expressionInput) {
        setValidationError(expressionInput, "Для заполненной строки нужна формула.");
        issues.push(`Формула #${index + 1}: добавь выражение.`);
      }

      if (!expression) {
        return;
      }

      const dependencies = parseFormulaIdentifiers(expression).filter(
        (identifier) => !FORMULA_PREVIEW_ALLOWED_FUNCTIONS.has(identifier)
      );
      dependencies.forEach((dependency) => {
        if (availableFormulaVariables.has(dependency)) {
          return;
        }
        const dependencyPosition = formulaKeyPosition.get(dependency);
        if (dependencyPosition === undefined) {
          setValidationError(
            expressionInput,
            `Неизвестная переменная '${dependency}'.`
          );
          issues.push(
            `Формула #${index + 1}: неизвестная переменная '${dependency}'.`
          );
          return;
        }
        if (dependencyPosition >= index) {
          setValidationError(
            expressionInput,
            `Ссылка на '${dependency}' ниже по списку.`
          );
          issues.push(
            `Формула #${index + 1}: ссылка на '${dependency}', объявленную ниже.`
          );
        }
      });
      availableFormulaVariables.add(formulaResolvedKeys[index]);
    });

    validateReportBlocks(clientReportBlockNode, "rt_client[]", "Клиентский отчёт", issues);
    validateReportBlocks(psychReportBlockNode, "rt_psychologist[]", "Профессиональный отчёт", issues);

    if (issues.length) {
      notify("error", issues[0]);
      return false;
    }
    return true;
  }

  if (manualForm) {
    manualForm.addEventListener("input", (event) => {
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) {
        removeValidationError(target);
        if (target.name !== "csrf_token") {
          markDraftDirty();
        }
      }
    });
    manualForm.addEventListener("change", (event) => {
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) {
        removeValidationError(target);
        if (target.name !== "csrf_token") {
          markDraftDirty();
        }
      }
    });
    manualForm.addEventListener("submit", (event) => {
      if (!validateBuilderForm()) {
        event.preventDefault();
        return;
      }
      saveDraftNow(true);
      notify("success", "Проверка пройдена, создаю тест...", 1600);
    });
  }

  const initialSectionTitles = [...sectionsNode.querySelectorAll("input[name='section_titles[]']")].map(
    (input) => input.value.trim()
  );
  sectionsNode.innerHTML = "";
  (initialSectionTitles.length ? initialSectionTitles : ["Профиль клиента"]).forEach((title) => {
    sectionsNode.appendChild(createSectionInput(title));
  });

  if (!questionsNode.children.length) {
    questionsNode.appendChild(createQuestionItem());
  }

  if (formulaNode && !formulaNode.children.length) {
    const sample = createFormulaItem({
      key: "adaptability_index",
      label: "Индекс адаптивности",
      expression: "round((score_percent + completion_percent) / 2, 2)",
      description: "Средняя оценка цифровых навыков и устойчивости к нагрузке",
    });
    formulaNode.appendChild(sample);
  }
  ensureReportBlockDefaults();
  syncEmptyStates();

  syncQuestionSections();
  syncFormulaPreviewContextInputs();
  initDraftControls();
})();
