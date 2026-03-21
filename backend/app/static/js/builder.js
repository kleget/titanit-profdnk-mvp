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

  if (!sectionsNode || !questionsNode || !addSectionBtn || !addQuestionBtn) {
    return;
  }

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
    box.innerHTML = `<p>${message}</p>`;
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

  function createSectionInput(value = "") {
    const wrapper = document.createElement("div");
    wrapper.className = "inline-form";
    const input = document.createElement("input");
    input.name = "section_titles[]";
    input.placeholder = "Название секции";
    input.required = true;
    input.value = value;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn small ghost";
    remove.textContent = "Удалить";
    remove.addEventListener("click", () => {
      wrapper.remove();
      syncQuestionSections();
      syncEmptyStates();
    });
    input.addEventListener("input", syncQuestionSections);

    wrapper.append(input, remove);
    return wrapper;
  }

  function createQuestionItem() {
    const box = document.createElement("div");
    box.className = "question-item";
    box.innerHTML = `
      <div class="inline-form">
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
      <label>Текст вопроса
        <input name="q_text[]" required placeholder="Введите формулировку вопроса">
      </label>
      <label>Опции (для choice): формат "Текст:балл, Текст2:балл"
        <input name="q_options[]" placeholder="Например: Доход:2, Стабильность:1">
      </label>
      <div class="inline-form">
        <label>Минимум
          <input type="number" step="any" name="q_min[]">
        </label>
        <label>Максимум
          <input type="number" step="any" name="q_max[]">
        </label>
        <label>Вес
          <input type="number" step="0.1" name="q_weight[]" value="1">
        </label>
      </div>
      <button type="button" class="btn small ghost remove-question">Удалить вопрос</button>
    `;

    const removeBtn = box.querySelector(".remove-question");
    removeBtn.addEventListener("click", () => {
      box.remove();
      syncEmptyStates();
    });
    return box;
  }

  function createFormulaItem() {
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
      <button type="button" class="btn small ghost remove-formula">Удалить формулу</button>
    `;

    const removeBtn = box.querySelector(".remove-formula");
    removeBtn.addEventListener("click", () => {
      box.remove();
      syncEmptyStates();
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
    });
    return box;
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
    });
    box.querySelector(".move-up").addEventListener("click", () => {
      const prev = box.previousElementSibling;
      if (prev) {
        box.parentNode.insertBefore(box, prev);
      }
    });
    box.querySelector(".move-down").addEventListener("click", () => {
      const next = box.nextElementSibling;
      if (next) {
        box.parentNode.insertBefore(next, box);
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
      sectionsNode.appendChild(createSectionInput(section.title || "Секция"));
    });
    syncQuestionSections();

    questionsNode.innerHTML = "";
    (preset.sections || []).forEach((section) => {
      (section.questions || []).forEach((question) => {
        const item = createQuestionItem();
        const sectionSelect = item.querySelector("select[name='q_section[]']");
        const typeSelect = item.querySelector("select[name='q_type[]']");
        const requiredSelect = item.querySelector("select[name='q_required[]']");
        const textInput = item.querySelector("input[name='q_text[]']");
        const optionsInput = item.querySelector("input[name='q_options[]']");
        const minInput = item.querySelector("input[name='q_min[]']");
        const maxInput = item.querySelector("input[name='q_max[]']");
        const weightInput = item.querySelector("input[name='q_weight[]']");

        if (sectionSelect) {
          sectionSelect.value = section.title || "Общая секция";
        }
        if (typeSelect) {
          typeSelect.value = question.question_type || "text";
        }
        if (requiredSelect) {
          requiredSelect.value = question.required ? "true" : "false";
        }
        if (textInput) {
          textInput.value = question.text || "";
        }
        if (optionsInput) {
          optionsInput.value = optionsToFlatValue(question.options_json);
        }
        if (minInput) {
          minInput.value =
            typeof question.min_value === "number" && Number.isFinite(question.min_value)
              ? String(question.min_value)
              : "";
        }
        if (maxInput) {
          maxInput.value =
            typeof question.max_value === "number" && Number.isFinite(question.max_value)
              ? String(question.max_value)
              : "";
        }
        if (weightInput) {
          const weight =
            typeof question.weight === "number" && Number.isFinite(question.weight)
              ? question.weight
              : 1;
          weightInput.value = String(weight);
        }
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
    notify("success", "Пресет применён. Проверьте детали и создайте тест.");
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
      const current = select.value;
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
    });
  }

  addSectionBtn.addEventListener("click", () => {
    sectionsNode.appendChild(createSectionInput());
    syncQuestionSections();
    syncEmptyStates();
  });

  addQuestionBtn.addEventListener("click", () => {
    questionsNode.appendChild(createQuestionItem());
    syncQuestionSections();
    syncEmptyStates();
  });

  if (addFormulaBtn && formulaNode) {
    addFormulaBtn.addEventListener("click", () => {
      formulaNode.appendChild(createFormulaItem());
      syncEmptyStates();
    });
  }

  if (addClientFieldBtn && clientFieldNode) {
    addClientFieldBtn.addEventListener("click", () => {
      clientFieldNode.appendChild(createClientFieldItem());
      syncEmptyStates();
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
    });
  }
  if (addPsychReportBlockBtn && psychReportBlockNode) {
    addPsychReportBlockBtn.addEventListener("click", () => {
      psychReportBlockNode.appendChild(createReportBlockItem("rt_psychologist[]"));
      syncEmptyStates();
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

  function parseChoiceOptions(value) {
    return (value || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
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

    const sectionInputs = [...sectionsNode.querySelectorAll("input[name='section_titles[]']")];
    if (!sectionInputs.length) {
      issues.push("Добавь хотя бы одну секцию.");
    }
    sectionInputs.forEach((input, index) => {
      if (!input.value.trim()) {
        setValidationError(input, "Название секции обязательно.");
        issues.push(`Секция #${index + 1}: пустое название.`);
      }
    });

    const questionItems = [...questionsNode.querySelectorAll(".question-item")];
    if (!questionItems.length) {
      issues.push("Добавь минимум один вопрос.");
    }
    questionItems.forEach((item, index) => {
      const qText = item.querySelector("input[name='q_text[]']");
      const qType = item.querySelector("select[name='q_type[]']");
      const qOptions = item.querySelector("input[name='q_options[]']");
      const qMin = item.querySelector("input[name='q_min[]']");
      const qMax = item.querySelector("input[name='q_max[]']");

      if (!qText || !qText.value.trim()) {
        if (qText) {
          setValidationError(qText, "Текст вопроса обязателен.");
        }
        issues.push(`Вопрос #${index + 1}: заполни формулировку.`);
      }

      const typeValue = qType?.value || "text";
      if (typeValue === "single_choice" || typeValue === "multiple_choice") {
        const options = parseChoiceOptions(qOptions?.value || "");
        if (options.length < 2) {
          if (qOptions) {
            setValidationError(qOptions, "Нужно минимум 2 опции через запятую.");
          }
          issues.push(`Вопрос #${index + 1}: для выбора нужно минимум 2 опции.`);
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
      }
    });
    manualForm.addEventListener("change", (event) => {
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) {
        removeValidationError(target);
      }
    });
    manualForm.addEventListener("submit", (event) => {
      if (!validateBuilderForm()) {
        event.preventDefault();
        return;
      }
      notify("success", "Проверка пройдена, создаю тест...", 1600);
    });
  }

  if (!questionsNode.children.length) {
    questionsNode.appendChild(createQuestionItem());
  }

  if (formulaNode && !formulaNode.children.length) {
    const sample = createFormulaItem();
    sample.querySelector("input[name='metric_key[]']").value = "adaptability_index";
    sample.querySelector("input[name='metric_label[]']").value = "Индекс адаптивности";
    sample.querySelector("input[name='metric_expression[]']").value =
      "round((digital_skill + stress_level) / 2, 2)";
    sample.querySelector("input[name='metric_description[]']").value =
      "Средняя оценка цифровых навыков и устойчивости к нагрузке";
    formulaNode.appendChild(sample);
  }
  ensureReportBlockDefaults();
  syncEmptyStates();

  syncQuestionSections();
})();
