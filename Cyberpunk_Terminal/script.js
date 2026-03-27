    document.addEventListener("DOMContentLoaded", () => {
      // 4. Staggered Fade-in
      const boxes = [
        document.querySelector('.lg\\:col-span-7'),
        document.querySelectorAll('aside section')[0],
        document.querySelectorAll('aside section')[1],
        document.querySelectorAll('aside section')[2]
      ];
      boxes.forEach(box => {
        if (box) {
          box.style.opacity = '0';
          box.style.transform = 'translateY(20px)';
          box.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
        }
      });

      boxes.forEach((box, index) => {
        if (box) {
          setTimeout(() => {
            box.style.opacity = '1';
            box.style.transform = 'translateY(0)';
          }, index * 500);
        }
      });

      // Local Link Logic
      const linkDisplay = document.getElementById('link-address');
      if (linkDisplay) {
        const linkStates = ['STABLE', '127.0.0.1', 'NODE_0x7F', 'ENCRYPTED'];
        let lIdx = 0;
        setInterval(() => {
          linkDisplay.textContent = linkStates[lIdx % linkStates.length];
          lIdx++;
        }, 4000);
      }

      // Hide Launch Button Area initially
      const inputArea = document.querySelector('.lg\\:col-span-7 .mt-auto');
      if (inputArea) {
        inputArea.style.opacity = '0';
        inputArea.style.pointerEvents = 'none';
        inputArea.style.transition = 'opacity 1s ease-in';
      }

      // AEGIS Events Animation
      const aegisLogs = [
        { text: "[08.21%] NODE_REGISTRY_SYNC... SUCCESS", color: "text-primary-fixed" },
        { text: "[14.55%] DECODING_SERIAL_HEADERS... COMPLETED", color: "text-primary-fixed" },
        { text: "[32.10%] WARNING: SCHEMA_ROTATION_DETECTED (V3.2)", color: "text-tertiary-fixed" },
        { text: "[56.88%] SCANNING_SLEEPER_NODES... 4 ANOMALIES FOUND", color: "text-secondary" },
        { text: "[78.42%] CRITICAL: UNKNOWN_CONTROLLER_INTRUSION_DETECTED", color: "text-[#FF0000]" },
        { text: "[99.99%] DATALINK_ESTABLISHED_WITH_AEGIS_CORE", color: "text-[#00ff41]" }
      ];

      const typeEventLogs = async () => {
        const container = document.getElementById('event-logs-container');
        const progressBar = document.getElementById('events-progress-bar');
        const progressStatus = document.getElementById('events-progress-status');

        for (let i = 0; i < aegisLogs.length; i++) {
          const logData = aegisLogs[i];
          const logEl = document.createElement('div');
          logEl.className = `event-log ${logData.color}`;
          logEl.innerHTML = `<span>${logData.text}</span><span class="tag-new">NEW</span>`;

          // Update Progress Bar
          const match = logData.text.match(/\[([\d.]+)%\]/);
          if (match && progressBar) {
            const percent = match[1];
            progressBar.style.width = percent + '%';
            if (percent === '99.99') {
              progressBar.classList.remove('bg-primary-fixed');
              progressBar.classList.add('bg-[#00ff41]');
              progressBar.classList.remove('pulse-bar');
              if (progressStatus) {
                progressStatus.textContent = "SYSTEM SCANNED";
                progressStatus.classList.remove('text-primary-fixed/50');
                progressStatus.classList.add('text-[#00ff41]');
              }
            }
          }

          // Remove previous NEW tags
          container.querySelectorAll('.tag-new').forEach(tag => tag.remove());

          container.appendChild(logEl);
          setTimeout(() => logEl.classList.add('show'), 10);

          container.scrollTop = container.scrollHeight;
          await new Promise(r => setTimeout(r, 200));
        }
      };

      const typeModuleRows = async (containerId) => {
        const rows = document.querySelectorAll(`#${containerId} > *`);
        for (const row of rows) {
          row.style.opacity = '1';
          row.style.transform = 'translateY(0)';
          // Add a tiny bit of typewriter feel by delaying between rows
          await new Promise(r => setTimeout(r, 200));
        }
      };

      // New True Typewriter Effect
      const startTerminalAnimation = () => {
        setTimeout(() => {
          const terminalContainer = document.querySelector('.lg\\:col-span-7 .p-6');
          const asciiLogo = terminalContainer.querySelector('.ascii-art');
          if (asciiLogo) asciiLogo.style.opacity = '1';
          const linesWrapper = terminalContainer.querySelector('.space-y-1');
          if (linesWrapper) linesWrapper.style.opacity = '1';

          const terminalLines = Array.from(document.querySelectorAll('.lg\\:col-span-7 .p-6 p, .lg\\:col-span-7 .p-6 .flex.items-center:not(.mt-auto *)'));

          terminalLines.forEach(line => {
            line.style.opacity = '0';
            line.style.display = 'none';
          });

          const scrollToBottom = () => {
            terminalContainer.scrollTop = terminalContainer.scrollHeight;
          };

          const typeText = async (element) => {
            element.style.display = element.tagName === 'DIV' ? 'flex' : 'block';
            element.style.opacity = '1';

            if (element.tagName === 'DIV' && element.classList.contains('items-center')) {
              return new Promise(resolve => {
                const progressBar = element.querySelector('.bg-primary-fixed.h-full');
                if (progressBar) {
                  progressBar.style.width = '0%';
                  progressBar.offsetHeight; // force reflow
                  progressBar.style.transition = 'width 2s linear';

                  setTimeout(() => {
                    progressBar.style.width = '100%';
                  }, 50);

                  const progressText = element.querySelector('span:last-child');
                  if (progressText) {
                    let p = 0;
                    const interval = setInterval(() => {
                      p += 1;
                      progressText.textContent = `] ${p}%`;
                      if (p >= 100) clearInterval(interval);
                    }, 20);
                  }

                  setTimeout(() => {
                    element.style.display = 'none';
                    resolve();
                  }, 2200);
                } else {
                  resolve();
                }
              });
            }

            const originalHTML = element.innerHTML;
            element.innerHTML = '';

            return new Promise(resolve => {
              let htmlContent = originalHTML;
              let isTag = false;
              let textContent = '';
              let index = 0;

              const typeChar = () => {
                if (index < htmlContent.length) {
                  if (htmlContent[index] === '<') isTag = true;

                  textContent += htmlContent[index];
                  index++;

                  if (isTag) {
                    if (htmlContent[index - 1] === '>') isTag = false;
                    typeChar();
                  } else {
                    element.innerHTML = textContent + '<span class="animate-pulse">_</span>';
                    scrollToBottom();
                    setTimeout(typeChar, 15);
                  }
                } else {
                  element.innerHTML = textContent;
                  resolve();
                }
              };
              typeChar();
            });
          };

          const processLines = async () => {
            let passedProgressBar = false;

            for (let i = 0; i < terminalLines.length; i++) {
              const line = terminalLines[i];

              if (line.tagName === 'DIV' && line.classList.contains('items-center')) {
                passedProgressBar = true;
              }

              await typeText(line);

              if (passedProgressBar && line.tagName === 'P') {
                line.style.opacity = '0.8';
                line.classList.add('text-primary-fixed');
              }

              await new Promise(r => setTimeout(r, 200));
            }

            if (inputArea) {
              inputArea.style.opacity = '1';
              inputArea.style.pointerEvents = 'auto';
              scrollToBottom();
            }
          };

          processLines();

        }, 500);
      };

      // Sequential Trigger
      const runAllAnimations = async () => {
        // Wait 1s after box fade-in
        await new Promise(r => setTimeout(r, 1000));
        await typeEventLogs();
        await typeModuleRows('settings-rows');
        await typeModuleRows('whoami-rows');
        startTerminalAnimation();
      };

      runAllAnimations();
    });

    function setStaticTimestamp() {
      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const seconds = String(now.getSeconds()).padStart(2, '0');

      const timestamp = `${hours}:${minutes}:${seconds}`;

      // Sirf ek baar value set hogi aur wahi rahegi
      const tsEl = document.getElementById('init-timestamp');
      if (tsEl) tsEl.textContent = timestamp;
    }

    // Page load par call karlo
    setStaticTimestamp();
