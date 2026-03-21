(function () {
  const sectionsNode = document.getElementById("sections");
  const questionsNode = document.getElementById("question-list");
  const formulaNode = document.getElementById("metric-formula-list");
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

  if (!sectionsNode || !questionsNode || !addSectionBtn || !addQuestionBtn) {
    return;
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
    removeBtn.addEventListener("click", () => box.remove());
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
    removeBtn.addEventListener("click", () => box.remove());
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
    box.querySelector(".remove-client-field").addEventListener("click", () => box.remove());
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

    box.querySelector(".remove-report-block").addEventListener("click", () => box.remove());
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
  });

  addQuestionBtn.addEventListener("click", () => {
    questionsNode.appendChild(createQuestionItem());
    syncQuestionSections();
  });

  if (addFormulaBtn && formulaNode) {
    addFormulaBtn.addEventListener("click", () => {
      formulaNode.appendChild(createFormulaItem());
    });
  }

  if (addClientFieldBtn && clientFieldNode) {
    addClientFieldBtn.addEventListener("click", () => {
      clientFieldNode.appendChild(createClientFieldItem());
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
    });
  }
  if (addPsychReportBlockBtn && psychReportBlockNode) {
    addPsychReportBlockBtn.addEventListener("click", () => {
      psychReportBlockNode.appendChild(createReportBlockItem("rt_psychologist[]"));
    });
  }
  reportTemplatePresetBtns.forEach((button) => {
    button.addEventListener("click", () => {
      applyReportTemplatePreset(button.dataset.template);
    });
  });

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

  syncQuestionSections();
})();
