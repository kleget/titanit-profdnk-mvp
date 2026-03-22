(function () {
  const form = document.getElementById("manual-builder");
  if (!form) {
    return;
  }

  const steps = Array.from(form.querySelectorAll("[data-builder-step]"));
  const stepButtons = Array.from(document.querySelectorAll("[data-step-target]"));
  const nextButtons = Array.from(form.querySelectorAll("[data-step-next]"));
  const prevButtons = Array.from(form.querySelectorAll("[data-step-prev]"));

  if (!steps.length) {
    return;
  }

  let currentIndex = Math.max(
    0,
    steps.findIndex((node) => node.classList.contains("is-active"))
  );
  if (currentIndex < 0) {
    currentIndex = 0;
  }

  function visibleFields(step) {
    return Array.from(step.querySelectorAll("input, select, textarea")).filter((field) => {
      if (field.disabled) {
        return false;
      }
      if (field.type === "hidden") {
        return false;
      }
      return true;
    });
  }

  function validateStep(index) {
    const step = steps[index];
    if (!step) {
      return true;
    }
    const fields = visibleFields(step);
    for (const field of fields) {
      if (typeof field.checkValidity === "function" && !field.checkValidity()) {
        if (typeof field.reportValidity === "function") {
          field.reportValidity();
        }
        field.scrollIntoView({ behavior: "smooth", block: "center" });
        return false;
      }
    }
    return true;
  }

  function setStep(nextIndex) {
    const clamped = Math.max(0, Math.min(steps.length - 1, nextIndex));
    currentIndex = clamped;

    steps.forEach((step, index) => {
      const active = index === clamped;
      step.classList.toggle("is-active", active);
      if (active) {
        step.removeAttribute("hidden");
      } else {
        step.setAttribute("hidden", "hidden");
      }
    });

    stepButtons.forEach((button, index) => {
      const target = Number(button.dataset.stepTarget || "0") - 1;
      const active = target === clamped || index === clamped;
      button.classList.toggle("is-active", active);
      if (active) {
        button.setAttribute("aria-current", "step");
      } else {
        button.removeAttribute("aria-current");
      }
    });

    const panel = steps[clamped];
    if (panel) {
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  nextButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (!validateStep(currentIndex)) {
        return;
      }
      setStep(currentIndex + 1);
    });
  });

  prevButtons.forEach((button) => {
    button.addEventListener("click", () => {
      setStep(currentIndex - 1);
    });
  });

  stepButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetIndex = Number(button.dataset.stepTarget || "0") - 1;
      if (!Number.isFinite(targetIndex)) {
        return;
      }
      if (targetIndex > currentIndex && !validateStep(currentIndex)) {
        return;
      }
      setStep(targetIndex);
    });
  });

  setStep(currentIndex);
})();
