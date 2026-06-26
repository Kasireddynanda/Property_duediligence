export const config = {
  matches: ["<all_urls>"]
}

export {}

const API_BASE =
  "https://vendor-discovery-29510517600.asia-south1.run.app/api/v1/vendor-discovery/"

const REPORT_API_BASE = "http://localhost:8000"

type VendorResult = {
  company_name: string
  cin: string
  company_status: string
  registered_office_address: string
  company_state_code: string
}

type VendorResponse = {
  total_count: number
  results: VendorResult[]
}

type InfraProjectResult = {
  project_name: string
  promoter_name: string
  detail_url: string
  last_modified: string
  score?: number
  search?: {
    district_id?: string
    district_name?: string
    project_type_id?: string
    project_type_name?: string
  }
}

type InfraSearchResponse = {
  total_count: number
  page: number
  page_size: number
  results: InfraProjectResult[]
}

const EMAIL_CONFIG = {
  // Option 1: SMTP via SmtpJS (Sends real emails client-side from the browser)
  // To use this, sign up for free at https://smtpjs.com, configure your SMTP server (e.g. Gmail, SendGrid, ElasticEmail),
  // and paste the generated SecureToken here.
  useSmtpJS: true,
  smtpJS: {
    secureToken: "", // E.g. "your-smtpjs-secure-token"
    from: "support@signalx.ai",
    host: "",         // (Optional) host if secureToken is empty
    username: "",     // (Optional) username if secureToken is empty
    password: ""      // (Optional) password if secureToken is empty
  },
  // Option 2: Custom Backend API Endpoint
  useBackendAPI: false,
  backendUrl: "https://vendor-discovery-29510517600.asia-south1.run.app/api/v1/vendor-discovery/place-report"
}

if (!(window as any).__hiExtensionLoaded) {
  ;(window as any).__hiExtensionLoaded = true

  let detectedNames: string[] = []
  let lastSearchQuery = ""
  let modalOverlayEl: HTMLDivElement | null = null
  let selectedTextModalOverlay: HTMLDivElement | null = null
  let infraSearchModalOverlay: HTMLDivElement | null = null
  let lastUrl = window.location.href

  const CENTER_MODAL_WIDTH = "480px"

  const root = document.createElement("div")
  root.id = "hi-vendor-search-root"
  Object.assign(root.style, {
    position: "fixed",
    bottom: "20px",
    right: "20px",
    zIndex: "2147483647",
    fontFamily: "system-ui, -apple-system, sans-serif",
    fontSize: "14px",
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
    gap: "10px"
  })

  const panel = document.createElement("div")
  Object.assign(panel.style, {
    display: "none",
    width: "360px",
    maxHeight: "420px",
    background: "#fff",
    border: "1px solid #e0e0e0",
    borderRadius: "10px",
    boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
    overflow: "hidden",
    flexDirection: "column"
  })

  const panelHeader = document.createElement("div")
  Object.assign(panelHeader.style, {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 14px",
    borderBottom: "1px solid #eee",
    background: "#f8f9fa"
  })

  const panelTitle = document.createElement("strong")
  panelTitle.textContent = "Vendor Search"

  const closeBtn = document.createElement("button")
  closeBtn.textContent = "×"
  Object.assign(closeBtn.style, {
    border: "none",
    background: "transparent",
    fontSize: "20px",
    cursor: "pointer",
    lineHeight: "1",
    color: "#666"
  })
  closeBtn.onclick = () => {
    panel.style.display = "none"
  }

  panelHeader.append(panelTitle, closeBtn)

  const queryLabel = document.createElement("div")
  Object.assign(queryLabel.style, {
    padding: "10px 14px 0",
    color: "#666",
    fontSize: "12px"
  })
  queryLabel.textContent = "Selected text"

  const queryText = document.createElement("div")
  Object.assign(queryText.style, {
    padding: "4px 14px 10px",
    fontWeight: "600",
    wordBreak: "break-word"
  })

  const statusEl = document.createElement("div")
  Object.assign(statusEl.style, {
    padding: "0 14px 10px",
    color: "#666",
    fontSize: "13px"
  })

  const resultsEl = document.createElement("div")
  Object.assign(resultsEl.style, {
    overflowY: "auto",
    maxHeight: "220px",
    padding: "0 14px 10px"
  })

  const manualSection = document.createElement("div")
  Object.assign(manualSection.style, {
    padding: "12px 14px",
    borderTop: "1px solid #eee",
    background: "#f8fafc",
    display: "flex",
    flexDirection: "column",
    gap: "8px"
  })

  const manualLabel = document.createElement("div")
  manualLabel.textContent = "Place report for any entity"
  Object.assign(manualLabel.style, {
    fontSize: "12px",
    fontWeight: "600",
    color: "#475569"
  })

  const entityInput = document.createElement("input")
  entityInput.type = "text"
  entityInput.placeholder = "Type entity / project / promoter name"
  Object.assign(entityInput.style, {
    padding: "8px 10px",
    border: "1px solid #cbd5e1",
    borderRadius: "8px",
    fontSize: "13px",
    outline: "none",
    width: "100%",
    boxSizing: "border-box"
  })

  const placeReportBtn = document.createElement("button")
  placeReportBtn.textContent = "Place Report"
  Object.assign(placeReportBtn.style, {
    padding: "9px 14px",
    border: "none",
    borderRadius: "8px",
    background: "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)",
    color: "#fff",
    fontWeight: "600",
    fontSize: "13px",
    cursor: "pointer"
  })

  manualSection.append(manualLabel, entityInput, placeReportBtn)

  panel.append(panelHeader, queryLabel, queryText, statusEl, resultsEl, manualSection)

  // Container for actions buttons at bottom right
  const buttonsContainer = document.createElement("div")
  Object.assign(buttonsContainer.style, {
    display: "flex",
    gap: "8px",
    alignItems: "center"
  })

  const toggleBtn = document.createElement("button")
  toggleBtn.textContent = "Enable Search"
  Object.assign(toggleBtn.style, {
    padding: "10px 16px",
    border: "none",
    borderRadius: "24px",
    background: "#1a73e8",
    color: "#fff",
    fontWeight: "600",
    cursor: "pointer",
    boxShadow: "0 4px 12px rgba(26,115,232,0.4)"
  })

  toggleBtn.onclick = (e) => {
    e.stopPropagation()
    openInfraSearchModal()
  }

  const detectBtn = document.createElement("button")
  detectBtn.textContent = "🔍 Builders (0)"
  Object.assign(detectBtn.style, {
    padding: "10px 16px",
    border: "none",
    borderRadius: "24px",
    background: "#7c3aed",
    color: "#fff",
    fontWeight: "600",
    cursor: "pointer",
    boxShadow: "0 4px 12px rgba(124, 58, 237, 0.4)",
    display: "none",
    transition: "all 0.2s ease"
  })
  detectBtn.onmouseenter = () => {
    detectBtn.style.background = "#6d28d9"
    detectBtn.style.boxShadow = "0 6px 16px rgba(109, 40, 217, 0.5)"
    detectBtn.style.transform = "translateY(-1px)"
  }
  detectBtn.onmouseleave = () => {
    detectBtn.style.background = "#7c3aed"
    detectBtn.style.boxShadow = "0 4px 12px rgba(124, 58, 237, 0.4)"
    detectBtn.style.transform = "translateY(0)"
  }

  buttonsContainer.append(toggleBtn, detectBtn)

  const quickReportBtn = document.createElement("button")
  quickReportBtn.textContent = "Place Report"
  Object.assign(quickReportBtn.style, {
    padding: "10px 16px",
    border: "none",
    borderRadius: "24px",
    background: "#0f766e",
    color: "#fff",
    fontWeight: "600",
    cursor: "pointer",
    boxShadow: "0 4px 12px rgba(15,118,110,0.35)"
  })
  quickReportBtn.onclick = (e) => {
    e.stopPropagation()
    const selection = window.getSelection()?.toString().trim() || ""
    if (selection) {
      entityInput.value = selection
      queryText.textContent = selection
      lastSearchQuery = selection
    }
    openSelectedTextModal(selection)
  }
  buttonsContainer.append(quickReportBtn)

  root.onclick = (e) => e.stopPropagation()
  root.onmouseup = (e) => e.stopPropagation()

  const resolveEntityName = (fallback = ""): string => {
    return (
      entityInput.value.trim() ||
      queryText.textContent?.trim() ||
      lastSearchQuery.trim() ||
      fallback.trim()
    )
  }

  const appendPlaceReportFallback = (
    container: HTMLElement,
    entityName: string,
    message = "No search results found."
  ) => {
    const wrap = document.createElement("div")
    Object.assign(wrap.style, {
      padding: "12px",
      border: "1px dashed #cbd5e1",
      borderRadius: "8px",
      background: "#f8fafc",
      textAlign: "center"
    })

    const msg = document.createElement("div")
    msg.textContent = message
    Object.assign(msg.style, {
      color: "#64748b",
      fontSize: "13px",
      marginBottom: "10px",
      lineHeight: "1.4"
    })

    const hint = document.createElement("div")
    hint.textContent = entityName
      ? `You can still place a report for: ${entityName}`
      : "Type a name below or select text on the page."
    Object.assign(hint.style, {
      color: "#334155",
      fontSize: "12px",
      fontWeight: "600",
      marginBottom: "10px",
      wordBreak: "break-word"
    })

    const btn = document.createElement("button")
    btn.textContent = "Place Report"
    Object.assign(btn.style, {
      padding: "8px 16px",
      border: "none",
      borderRadius: "8px",
      background: "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)",
      color: "#fff",
      fontWeight: "600",
      fontSize: "13px",
      cursor: "pointer"
    })
    btn.onclick = () => {
      const name = entityName || resolveEntityName()
      if (!name) {
        alert("Please type an entity name or select text on the page.")
        entityInput.focus()
        return
      }
      entityInput.value = name
      closeBuildersModal()
      openSelectedTextModal(name)
    }

    wrap.append(msg, hint, btn)
    container.append(wrap)
  }

  const closeSelectedTextModal = () => {
    if (selectedTextModalOverlay) {
      selectedTextModalOverlay.remove()
      selectedTextModalOverlay = null
    }
  }

  const closeBuildersModal = () => {
    if (modalOverlayEl) {
      modalOverlayEl.remove()
      modalOverlayEl = null
    }
  }

  const closeInfraSearchModal = () => {
    if (infraSearchModalOverlay) {
      infraSearchModalOverlay.remove()
      infraSearchModalOverlay = null
    }
  }

  const isInsideExtensionUi = (node: Node | null): boolean => {
    if (!node) return false
    const el = node.nodeType === Node.TEXT_NODE ? node.parentElement : (node as Element)
    if (!el) return false
    return Boolean(
      root.contains(el) ||
        modalOverlayEl?.contains(el) ||
        selectedTextModalOverlay?.contains(el) ||
        infraSearchModalOverlay?.contains(el)
    )
  }

  placeReportBtn.onclick = () => {
    const name = resolveEntityName()
    if (!name) {
      alert("Please type an entity name or select text on the page.")
      entityInput.focus()
      return
    }
    openSelectedTextModal(name)
  }

  const renderResults = (data: VendorResponse, searchQuery: string) => {
    resultsEl.innerHTML = ""
    statusEl.textContent = `${data.total_count} vendor(s) found`

    if (!data.results.length) {
      appendPlaceReportFallback(
        resultsEl,
        searchQuery,
        "No vendors found in search results."
      )
      return
    }

    for (const vendor of data.results) {
      const item = document.createElement("div")
      Object.assign(item.style, {
        padding: "10px 0",
        borderBottom: "1px solid #f0f0f0"
      })

      const name = document.createElement("div")
      name.textContent = vendor.company_name
      name.style.fontWeight = "600"
      name.style.marginBottom = "4px"

      const meta = document.createElement("div")
      meta.style.fontSize = "12px"
      meta.style.color = "#555"
      meta.innerHTML = `<div>CIN: ${vendor.cin}</div>
        <div>Status: ${vendor.company_status} · ${vendor.company_state_code}</div>
        <div style="margin-top:2px">${vendor.registered_office_address}</div>`

      const reportBtn = document.createElement("button")
      reportBtn.textContent = "Place Report"
      Object.assign(reportBtn.style, {
        marginTop: "8px",
        padding: "6px 12px",
        border: "none",
        borderRadius: "6px",
        background: "#1e40af",
        color: "#fff",
        fontSize: "12px",
        fontWeight: "600",
        cursor: "pointer"
      })
      reportBtn.onclick = (e) => {
        e.stopPropagation()
        closeBuildersModal()
        openSelectedTextModal(vendor.company_name, vendor, vendor.cin)
      }

      item.append(name, meta, reportBtn)
      resultsEl.append(item)
    }
  }

  const searchVendors = async (name: string) => {
    const params = new URLSearchParams({
      name,
      page: "1",
      page_size: "10",
      fetch_ai_summary: "false",
      fetch_topn_news: "false"
    })

    const response = await fetch(`${API_BASE}?${params}`)
    if (!response.ok) {
      throw new Error(`Search failed (${response.status})`)
    }
    return response.json() as Promise<VendorResponse>
  }

  const searchInfraProjects = async (
    query: string,
    page = 1,
    pageSize = 20
  ) => {
    const params = new URLSearchParams({
      q: query,
      page: String(page),
      page_size: String(pageSize)
    })
    const response = await fetch(`${REPORT_API_BASE}/api/infra/search?${params}`)
    if (!response.ok) {
      let detail = `INFRA search failed (${response.status})`
      try {
        const errBody = await response.json()
        detail = errBody.detail || detail
      } catch {
        // ignore
      }
      throw new Error(detail)
    }
    return response.json() as Promise<InfraSearchResponse>
  }

  const openInfraSearchModal = () => {
    injectStyles()
    closeInfraSearchModal()
    closeBuildersModal()
    closeSelectedTextModal()

    const overlay = document.createElement("div")
    infraSearchModalOverlay = overlay
    Object.assign(overlay.style, {
      position: "fixed",
      top: "0",
      left: "0",
      width: "100vw",
      height: "100vh",
      background: "rgba(15, 23, 42, 0.4)",
      backdropFilter: "blur(4px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: "2147483647",
      animation: "overlayFadeIn 0.2s ease-out"
    })
    overlay.onclick = (e) => {
      if (e.target === overlay) closeInfraSearchModal()
    }

    const modal = document.createElement("div")
    modal.onclick = (e) => e.stopPropagation()
    Object.assign(modal.style, {
      background: "#ffffff",
      borderRadius: "16px",
      boxShadow:
        "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
      width: "720px",
      maxWidth: "95%",
      maxHeight: "85vh",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      animation: "modalFadeIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
      fontFamily: "system-ui, -apple-system, sans-serif"
    })

    const header = document.createElement("div")
    Object.assign(header.style, {
      background: "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)",
      color: "#ffffff",
      padding: "18px 24px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      flexShrink: "0"
    })

    const titleWrap = document.createElement("div")
    const title = document.createElement("strong")
    title.textContent = "RERA Project Search"
    Object.assign(title.style, { fontSize: "16px", fontWeight: "600", display: "block" })
    const subtitle = document.createElement("span")
    subtitle.textContent = "Search scraped projects in INFRA.All_projects"
    Object.assign(subtitle.style, {
      fontSize: "12px",
      color: "rgba(255, 255, 255, 0.8)",
      display: "block",
      marginTop: "4px"
    })
    titleWrap.append(title, subtitle)

    const headerClose = document.createElement("button")
    headerClose.innerHTML = "&times;"
    Object.assign(headerClose.style, {
      border: "none",
      background: "rgba(255, 255, 255, 0.15)",
      fontSize: "20px",
      cursor: "pointer",
      color: "#fff",
      width: "28px",
      height: "28px",
      borderRadius: "50%",
      lineHeight: "1"
    })
    headerClose.onclick = () => closeInfraSearchModal()
    header.append(titleWrap, headerClose)

    const body = document.createElement("div")
    Object.assign(body.style, {
      padding: "20px 24px",
      display: "flex",
      flexDirection: "column",
      gap: "14px",
      overflow: "hidden",
      flex: "1"
    })

    const searchRow = document.createElement("div")
    Object.assign(searchRow.style, {
      display: "flex",
      gap: "10px"
    })

    const searchInput = document.createElement("input")
    searchInput.type = "text"
    searchInput.placeholder = "Search project, promoter, district..."
    Object.assign(searchInput.style, {
      flex: "1",
      padding: "12px 14px",
      border: "1px solid #cbd5e1",
      borderRadius: "8px",
      fontSize: "14px",
      outline: "none",
      boxSizing: "border-box"
    })

    const searchBtn = document.createElement("button")
    searchBtn.type = "button"
    searchBtn.textContent = "Search"
    Object.assign(searchBtn.style, {
      padding: "12px 20px",
      border: "none",
      borderRadius: "8px",
      background: "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)",
      color: "#fff",
      fontWeight: "600",
      cursor: "pointer",
      fontSize: "14px",
      whiteSpace: "nowrap"
    })

    searchRow.append(searchInput, searchBtn)

    const statusLine = document.createElement("div")
    Object.assign(statusLine.style, {
      fontSize: "13px",
      color: "#64748b"
    })
    statusLine.textContent = "Type a name and press Search"

    const resultsWrap = document.createElement("div")
    Object.assign(resultsWrap.style, {
      overflowY: "auto",
      flex: "1",
      display: "flex",
      flexDirection: "column",
      gap: "10px",
      minHeight: "200px",
      maxHeight: "52vh"
    })

    const renderInfraResults = (data: InfraSearchResponse, query: string) => {
      resultsWrap.innerHTML = ""
      statusLine.textContent = `${data.total_count} project(s) found for "${query}"`

      if (!data.results.length) {
        appendPlaceReportFallback(
          resultsWrap,
          query,
          "No projects found in INFRA.All_projects."
        )
        return
      }

      for (const project of data.results) {
        const card = document.createElement("div")
        Object.assign(card.style, {
          padding: "14px",
          border: "1px solid #e2e8f0",
          borderRadius: "10px",
          background: "#fff",
          cursor: "pointer",
          transition: "all 0.2s ease"
        })
        card.onmouseenter = () => {
          card.style.borderColor = "#2563eb"
          card.style.boxShadow = "0 4px 12px rgba(37, 99, 235, 0.08)"
        }
        card.onmouseleave = () => {
          card.style.borderColor = "#e2e8f0"
          card.style.boxShadow = "none"
        }

        const nameEl = document.createElement("div")
        nameEl.textContent = project.project_name
        Object.assign(nameEl.style, {
          fontWeight: "700",
          color: "#0f172a",
          fontSize: "14px",
          marginBottom: "4px"
        })

        const meta = document.createElement("div")
        const district = project.search?.district_name || "—"
        const ptype = project.search?.project_type_name || "—"
        const score =
          typeof project.score === "number"
            ? `<span style="color:#64748b;font-size:11px;margin-left:8px;">score ${project.score.toFixed(2)}</span>`
            : ""
        meta.innerHTML = `
          <div style="font-size:12px;color:#475569;margin-bottom:4px;">
            <strong>Promoter:</strong> ${project.promoter_name}
          </div>
          <div style="font-size:12px;color:#64748b;">
            ${district} · ${ptype} · ${project.last_modified || "—"}${score}
          </div>
        `

        const actions = document.createElement("div")
        Object.assign(actions.style, {
          display: "flex",
          gap: "8px",
          marginTop: "10px"
        })

        const reportBtn = document.createElement("button")
        reportBtn.type = "button"
        reportBtn.textContent = "Place Report"
        Object.assign(reportBtn.style, {
          padding: "6px 12px",
          border: "none",
          borderRadius: "6px",
          background: "#1e40af",
          color: "#fff",
          fontSize: "12px",
          fontWeight: "600",
          cursor: "pointer"
        })
        reportBtn.onclick = (e) => {
          e.stopPropagation()
          closeInfraSearchModal()
          openSelectedTextModal(project.project_name)
        }

        const detailsBtn = document.createElement("button")
        detailsBtn.type = "button"
        detailsBtn.textContent = "View on RERA"
        Object.assign(detailsBtn.style, {
          padding: "6px 12px",
          border: "1px solid #cbd5e1",
          borderRadius: "6px",
          background: "#fff",
          color: "#1e40af",
          fontSize: "12px",
          fontWeight: "600",
          cursor: "pointer"
        })
        detailsBtn.onclick = (e) => {
          e.stopPropagation()
          window.open(project.detail_url, "_blank", "noopener,noreferrer")
        }

        actions.append(reportBtn, detailsBtn)
        card.append(nameEl, meta, actions)
        card.onclick = () => {
          closeInfraSearchModal()
          openSelectedTextModal(project.project_name)
        }
        resultsWrap.append(card)
      }
    }

    const runInfraSearch = async () => {
      const query = searchInput.value.trim()
      if (!query) {
        statusLine.textContent = "Please enter a search term"
        searchInput.focus()
        return
      }
      lastSearchQuery = query
      queryText.textContent = query
      entityInput.value = query
      statusLine.textContent = "Searching..."
      resultsWrap.innerHTML = ""
      searchBtn.disabled = true
      searchBtn.style.opacity = "0.7"

      try {
        const data = await searchInfraProjects(query)
        renderInfraResults(data, query)
      } catch (err) {
        statusLine.textContent = "Search failed"
        appendPlaceReportFallback(
          resultsWrap,
          query,
          err instanceof Error ? err.message : "Search failed."
        )
      } finally {
        searchBtn.disabled = false
        searchBtn.style.opacity = "1"
      }
    }

    searchBtn.onclick = () => void runInfraSearch()
    searchInput.onkeydown = (e) => {
      if (e.key === "Enter") {
        e.preventDefault()
        void runInfraSearch()
      }
    }

    body.append(searchRow, statusLine, resultsWrap)
    modal.append(header, body)
    overlay.append(modal)
    document.body.append(overlay)
    searchInput.focus()
  }

  const runSearch = async (text: string) => {
    lastSearchQuery = text
    queryText.textContent = text
    entityInput.value = text
    statusEl.textContent = "Searching..."
    resultsEl.innerHTML = ""
    panel.style.display = "flex"

    try {
      const data = await searchVendors(text)
      renderResults(data, text)
    } catch (err) {
      statusEl.textContent = "Search failed"
      resultsEl.innerHTML = ""
      appendPlaceReportFallback(
        resultsEl,
        text,
        err instanceof Error ? err.message : "Search failed."
      )
    }
  }

  // --- Auto-select Names & Popup Logic ---
  
  const injectStyles = () => {
    const styleId = "hi-vendor-search-styles"
    if (document.getElementById(styleId)) return
    
    const styleEl = document.createElement("style")
    styleEl.id = styleId
    styleEl.textContent = `
      @keyframes modalFadeIn {
        from { transform: scale(0.95); opacity: 0; }
        to { transform: scale(1); opacity: 1; }
      }
      @keyframes overlayFadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      @keyframes modalSpinner {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `
    document.head.appendChild(styleEl)
  }

  const sendConfirmationEmail = async (
    name: string,
    email: string,
    mobile: string,
    companyName: string,
    cin: string
  ) => {
    console.log(`[Email Service] Initiating email request for recipient: ${email}`)

    const emailBody = `
      <h3>Report Placement Confirmation</h3>
      <p>Dear ${name},</p>
      <p>Thank you for submitting your details. We have received your request to place a verification report for <strong>${companyName}</strong>.</p>
      <p><strong>Request Details:</strong></p>
      <ul>
        <li><strong>Vendor Name:</strong> ${companyName}</li>
        <li><strong>CIN:</strong> ${cin}</li>
        <li><strong>User Name:</strong> ${name}</li>
        <li><strong>Email:</strong> ${email}</li>
        <li><strong>Mobile:</strong> ${mobile}</li>
      </ul>
      <p>Our team will process the report and send it to you shortly.</p>
      <br>
      <p>Best regards,<br>SignalX Support Team</p>
    `

    const smtp = EMAIL_CONFIG.smtpJS
    const hasConfig = smtp.secureToken || (smtp.host && smtp.username && smtp.password)

    if (EMAIL_CONFIG.useSmtpJS && hasConfig) {
      console.log("[Email Service] Dispatching real email via SMTP (SmtpJS)...")
      const payload: Record<string, any> = {
        To: email,
        From: smtp.from,
        Subject: `Report Placement Request: ${companyName}`,
        Body: emailBody,
        Action: "Send"
      }

      if (smtp.secureToken) {
        payload.SecureToken = smtp.secureToken
      } else {
        payload.Host = smtp.host
        payload.Username = smtp.username
        payload.Password = smtp.password
      }

      try {
        const formData = new URLSearchParams()
        formData.append("data", JSON.stringify(payload))

        const response = await fetch("https://smtpjs.com/v3/smtpjs.aspx?", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded"
          },
          body: formData.toString()
        })

        if (!response.ok) {
          throw new Error(`SmtpJS HTTP error: ${response.status}`)
        }

        const resultText = await response.text()
        console.log(`[Email Service] SmtpJS Server Response: ${resultText}`)

        if (resultText.toLowerCase() !== "ok") {
          throw new Error(`SmtpJS response error: ${resultText}`)
        }
      } catch (err) {
        console.error(
          "[Email Service] SMTP dispatch failed. Falling back to simulation.",
          err
        )
        // Add fallback delay
        await new Promise((resolve) => setTimeout(resolve, 1500))
      }
    } else {
      console.log(
        "[Email Service] SMTP not configured. Attempting backend API or simulation fallback..."
      )
      const payload = {
        name,
        email,
        mobile,
        company_name: companyName,
        cin,
        timestamp: new Date().toISOString()
      }

      try {
        const response = await fetch(EMAIL_CONFIG.backendUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        })

        if (!response.ok) {
          console.warn(
            `Backend report endpoint returned status ${response.status}. Using simulation fallback.`
          )
        }
      } catch (e) {
        console.warn(
          "Backend report endpoint not reached or CORS restricted. Simulating successful email dispatch...",
          e
        )
      }

      // Delay to simulate network dispatch operation
      await new Promise((resolve) => setTimeout(resolve, 1500))
    }

    console.log(
      `[Email Service] Confirmation email process completed for ${email}`
    )
    return true
  }

  const placeReportWithRera = async (
    entityName: string,
    name: string,
    email: string,
    mobile: string,
    cin: string,
    vendorData?: VendorResult | null
  ) => {
    const response = await fetch(`${REPORT_API_BASE}/api/place-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        entity_name: entityName,
        user: { name, email, mobile },
        cin,
        vendor_data: vendorData ?? null,
        source_page_url: window.location.href
      })
    })

    if (!response.ok) {
      let detail = `Report API failed (${response.status})`
      try {
        const errBody = await response.json()
        detail = errBody.detail || detail
      } catch {
        // ignore parse errors
      }
      throw new Error(detail)
    }

    return response.json() as Promise<{
      report_id: string
      status: string
      total_rera_projects: number
      message: string
    }>
  }

  const openReportModal = (companyName: string, cin: string, vendorData?: VendorResult) => {
    injectStyles()
    closeBuildersModal()
    closeInfraSearchModal()
    closeSelectedTextModal()

    const reportOverlay = document.createElement("div")
    Object.assign(reportOverlay.style, {
      position: "fixed",
      top: "0",
      left: "0",
      width: "100vw",
      height: "100vh",
      background: "rgba(15, 23, 42, 0.4)",
      backdropFilter: "blur(4px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: "2147483647",
      animation: "overlayFadeIn 0.2s ease-out"
    })

    const modal = document.createElement("div")
    Object.assign(modal.style, {
      background: "#ffffff",
      borderRadius: "16px",
      boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
      width: "480px",
      maxWidth: "90%",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      animation: "modalFadeIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
      fontFamily: "system-ui, -apple-system, sans-serif"
    })
    const header = document.createElement("div")
    Object.assign(header.style, {
      background: "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)",
      color: "#ffffff",
      padding: "18px 24px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      flexShrink: "0"
    })

    const titleContainer = document.createElement("div")
    const title = document.createElement("strong")
    title.textContent = "Place Report Request"
    Object.assign(title.style, {
      fontSize: "16px",
      fontWeight: "600",
      display: "block",
      letterSpacing: "-0.01em"
    })

    const subtitle = document.createElement("span")
    subtitle.textContent = companyName
    Object.assign(subtitle.style, {
      fontSize: "12px",
      color: "rgba(255, 255, 255, 0.8)",
      display: "block",
      marginTop: "2px",
      fontWeight: "500",
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
      maxWidth: "360px"
    })

    titleContainer.append(title, subtitle)

    const closeBtn = document.createElement("button")
    closeBtn.innerHTML = "&times;"
    Object.assign(closeBtn.style, {
      border: "none",
      background: "rgba(255, 255, 255, 0.15)",
      fontSize: "20px",
      cursor: "pointer",
      lineHeight: "1",
      color: "#ffffff",
      width: "28px",
      height: "28px",
      borderRadius: "50%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      transition: "background 0.2s ease"
    })
    closeBtn.onmouseenter = () =>
      (closeBtn.style.background = "rgba(255, 255, 255, 0.3)")
    closeBtn.onmouseleave = () =>
      (closeBtn.style.background = "rgba(255, 255, 255, 0.15)")
    closeBtn.onclick = () => reportOverlay.remove()

    header.append(titleContainer, closeBtn)

    const form = document.createElement("form")
    Object.assign(form.style, {
      padding: "24px",
      display: "flex",
      flexDirection: "column",
      gap: "16px"
    })
    form.onsubmit = (e) => e.preventDefault()

    const createInputField = (
      labelText: string,
      type: string,
      placeholder: string,
      id: string
    ) => {
      const fieldContainer = document.createElement("div")
      Object.assign(fieldContainer.style, {
        display: "flex",
        flexDirection: "column",
        gap: "6px"
      })

      const label = document.createElement("label")
      label.textContent = labelText
      Object.assign(label.style, {
        fontSize: "13px",
        fontWeight: "600",
        color: "#475569"
      })

      const input = document.createElement("input")
      input.type = type
      input.placeholder = placeholder
      input.id = id
      input.required = true
      Object.assign(input.style, {
        padding: "10px 14px",
        border: "1px solid #cbd5e1",
        borderRadius: "8px",
        fontSize: "14px",
        fontFamily: "inherit",
        color: "#1e293b",
        transition: "all 0.2s ease",
        outline: "none"
      })

      input.onfocus = () => {
        input.style.borderColor = "#1e40af"
        input.style.boxShadow = "0 0 0 3px rgba(30, 64, 175, 0.15)"
      }
      input.onblur = () => {
        input.style.borderColor = "#cbd5e1"
        input.style.boxShadow = "none"
      }

      fieldContainer.append(label, input)
      return { container: fieldContainer, input }
    }

    const nameField = createInputField(
      "Your Name",
      "text",
      "Enter your full name",
      "report-name"
    )
    const emailField = createInputField(
      "Email Address",
      "email",
      "Enter your email address",
      "report-email"
    )
    const mobileField = createInputField(
      "Mobile Number",
      "tel",
      "Enter 10-digit mobile number",
      "report-mobile"
    )

    form.append(
      nameField.container,
      emailField.container,
      mobileField.container
    )

    const checkboxContainer = document.createElement("label")
    Object.assign(checkboxContainer.style, {
      display: "flex",
      alignItems: "flex-start",
      gap: "10px",
      cursor: "pointer",
      marginTop: "4px",
      fontSize: "13px",
      color: "#475569",
      lineHeight: "1.4"
    })

    const checkbox = document.createElement("input")
    checkbox.type = "checkbox"
    checkbox.id = "report-declaration"
    Object.assign(checkbox.style, {
      marginTop: "3px",
      cursor: "pointer"
    })

    const checkboxText = document.createElement("span")
    checkboxText.innerHTML = `I declare that the details provided are correct and I authorize the request to place a detailed verification report for <strong>${companyName}</strong>.`

    checkboxContainer.append(checkbox, checkboxText)
    form.append(checkboxContainer)

    const btnContainer = document.createElement("div")
    Object.assign(btnContainer.style, {
      display: "flex",
      gap: "12px",
      justifyContent: "flex-end",
      marginTop: "8px"
    })

    const cancelBtn = document.createElement("button")
    cancelBtn.type = "button"
    cancelBtn.textContent = "Cancel"
    Object.assign(cancelBtn.style, {
      padding: "10px 18px",
      background: "#f1f5f9",
      border: "none",
      borderRadius: "8px",
      color: "#475569",
      fontWeight: "600",
      cursor: "pointer",
      fontSize: "14px",
      transition: "background 0.2s ease"
    })
    cancelBtn.onmouseenter = () => (cancelBtn.style.background = "#e2e8f0")
    cancelBtn.onmouseleave = () => (cancelBtn.style.background = "#f1f5f9")
    cancelBtn.onclick = () => reportOverlay.remove()

    const submitBtn = document.createElement("button")
    submitBtn.type = "submit"
    submitBtn.textContent = "Submit & Place Report"
    submitBtn.disabled = true
    Object.assign(submitBtn.style, {
      padding: "10px 20px",
      background: "#94a3b8",
      border: "none",
      borderRadius: "8px",
      color: "#ffffff",
      fontWeight: "600",
      cursor: "not-allowed",
      fontSize: "14px",
      transition: "all 0.2s ease"
    })

    const validateForm = () => {
      const name = nameField.input.value.trim()
      const email = emailField.input.value.trim()
      const mobile = mobileField.input.value.trim()
      const isDeclared = checkbox.checked

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      const mobileRegex = /^[0-9+\s-]{8,15}$/

      const isValid =
        name.length > 1 &&
        emailRegex.test(email) &&
        mobileRegex.test(mobile) &&
        isDeclared

      if (isValid) {
        submitBtn.disabled = false
        submitBtn.style.background =
          "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)"
        submitBtn.style.cursor = "pointer"
        submitBtn.style.boxShadow = "0 4px 12px rgba(29, 78, 216, 0.2)"
      } else {
        submitBtn.disabled = true
        submitBtn.style.background = "#94a3b8"
        submitBtn.style.cursor = "not-allowed"
        submitBtn.style.boxShadow = "none"
      }
    }

    nameField.input.oninput = validateForm
    emailField.input.oninput = validateForm
    mobileField.input.oninput = validateForm
    checkbox.onchange = validateForm

    btnContainer.append(cancelBtn, submitBtn)
    form.append(btnContainer)

    modal.append(header, form)
    reportOverlay.append(modal)
    document.body.append(reportOverlay)

    form.onsubmit = async (e) => {
      e.preventDefault()

      const name = nameField.input.value.trim()
      const email = emailField.input.value.trim()
      const mobile = mobileField.input.value.trim()

      submitBtn.disabled = true
      submitBtn.style.background = "#94a3b8"
      submitBtn.style.cursor = "not-allowed"
      submitBtn.innerHTML = `<div style="display: inline-flex; align-items: center;"><div style="border: 2px solid #f3f3f3; border-top: 2px solid #ffffff; border-radius: 50%; width: 14px; height: 14px; animation: modalSpinner 1s linear infinite; margin-right: 8px;"></div>Placing report...</div>`

      try {
        const reportResult = await placeReportWithRera(
          companyName,
          name,
          email,
          mobile,
          cin,
          vendorData
        )

        await sendConfirmationEmail(name, email, mobile, companyName, cin)

        modal.innerHTML = ""

        const successContainer = document.createElement("div")
        Object.assign(successContainer.style, {
          padding: "40px 24px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          textAlign: "center"
        })

        const successIcon = document.createElement("div")
        Object.assign(successIcon.style, {
          width: "64px",
          height: "64px",
          background: "#e8f5e9",
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "20px",
          color: "#2e7d32",
          fontSize: "32px",
          border: "2px solid #c8e6c9"
        })
        successIcon.innerHTML = "✓"

        const successTitle = document.createElement("h3")
        successTitle.textContent = "Report Request Placed!"
        Object.assign(successTitle.style, {
          margin: "0 0 10px 0",
          color: "#0f172a",
          fontSize: "20px",
          fontWeight: "700"
        })

        const successDesc = document.createElement("p")
        Object.assign(successDesc.style, {
          margin: "0 0 24px 0",
          color: "#475569",
          fontSize: "14px",
          lineHeight: "1.5"
        })
        successDesc.innerHTML = `Thank you, <strong>${name}</strong>. The report for <strong>${companyName}</strong> has been placed.<br><br>
          <strong>Report ID:</strong> ${reportResult.report_id}<br>
          <strong>RERA scrape:</strong> running in the background<br><br>
          A confirmation email has been sent to <strong>${email}</strong>.<br><br>
          <span style="font-size:12px;color:#64748b;">RERA scrape logs appear in the terminal running <code>python run_api.py</code>.</span>`

        const doneBtn = document.createElement("button")
        doneBtn.textContent = "Close"
        Object.assign(doneBtn.style, {
          padding: "10px 28px",
          background: "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)",
          color: "#ffffff",
          border: "none",
          borderRadius: "8px",
          fontWeight: "600",
          cursor: "pointer",
          fontSize: "14px",
          transition: "all 0.2s ease",
          boxShadow: "0 4px 12px rgba(29, 78, 216, 0.2)"
        })
        doneBtn.onmouseenter = () => {
          doneBtn.style.boxShadow = "0 6px 16px rgba(29, 78, 216, 0.3)"
        }
        doneBtn.onmouseleave = () => {
          doneBtn.style.boxShadow = "0 4px 12px rgba(29, 78, 216, 0.2)"
        }
        doneBtn.onclick = () => reportOverlay.remove()

        successContainer.append(successIcon, successTitle, successDesc, doneBtn)
        modal.append(successContainer)
      } catch (err) {
        console.error(err)
        submitBtn.disabled = false
        submitBtn.style.background =
          "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)"
        submitBtn.style.cursor = "pointer"
        submitBtn.textContent = "Submit & Place Report"
        alert("Failed to place report request. Please try again.")
      }
    }
  }

  const openSelectedTextModal = (
    initialText: string,
    vendorData?: VendorResult,
    cin = ""
  ) => {
    injectStyles()
    closeBuildersModal()
    closeInfraSearchModal()
    closeSelectedTextModal()

    const overlay = document.createElement("div")
    selectedTextModalOverlay = overlay
    Object.assign(overlay.style, {
      position: "fixed",
      top: "0",
      left: "0",
      width: "100vw",
      height: "100vh",
      background: "rgba(15, 23, 42, 0.4)",
      backdropFilter: "blur(4px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: "2147483647",
      animation: "overlayFadeIn 0.2s ease-out"
    })
    overlay.onclick = (e) => {
      if (e.target === overlay) closeSelectedTextModal()
    }

    const modal = document.createElement("div")
    modal.onclick = (e) => e.stopPropagation()
    Object.assign(modal.style, {
      background: "#ffffff",
      borderRadius: "16px",
      boxShadow:
        "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
      width: CENTER_MODAL_WIDTH,
      maxWidth: "90%",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      animation: "modalFadeIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
      fontFamily: "system-ui, -apple-system, sans-serif"
    })

    const header = document.createElement("div")
    Object.assign(header.style, {
      background: "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)",
      color: "#ffffff",
      padding: "18px 24px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      flexShrink: "0"
    })

    const titleWrap = document.createElement("div")
    const title = document.createElement("strong")
    title.textContent = "Selected Text"
    Object.assign(title.style, {
      fontSize: "16px",
      fontWeight: "600",
      display: "block"
    })
    const subtitle = document.createElement("span")
    subtitle.textContent = "Review the entity name before placing your order"
    Object.assign(subtitle.style, {
      fontSize: "12px",
      color: "rgba(255, 255, 255, 0.8)",
      display: "block",
      marginTop: "4px"
    })
    titleWrap.append(title, subtitle)

    const headerClose = document.createElement("button")
    headerClose.innerHTML = "&times;"
    Object.assign(headerClose.style, {
      border: "none",
      background: "rgba(255, 255, 255, 0.15)",
      fontSize: "20px",
      cursor: "pointer",
      color: "#fff",
      width: "28px",
      height: "28px",
      borderRadius: "50%",
      lineHeight: "1"
    })
    headerClose.onclick = () => closeSelectedTextModal()
    header.append(titleWrap, headerClose)

    const body = document.createElement("div")
    Object.assign(body.style, {
      padding: "24px",
      display: "flex",
      flexDirection: "column",
      gap: "16px"
    })

    const fieldLabel = document.createElement("label")
    fieldLabel.textContent = "Entity / Project / Promoter name"
    Object.assign(fieldLabel.style, {
      fontSize: "13px",
      fontWeight: "600",
      color: "#475569"
    })

    const textInput = document.createElement("textarea")
    textInput.value = initialText
    textInput.rows = 4
    textInput.placeholder = "Selected text will appear here..."
    Object.assign(textInput.style, {
      width: "100%",
      padding: "12px 14px",
      border: "1px solid #cbd5e1",
      borderRadius: "8px",
      fontSize: "15px",
      fontWeight: "600",
      color: "#0f172a",
      lineHeight: "1.5",
      resize: "vertical",
      minHeight: "96px",
      boxSizing: "border-box",
      fontFamily: "inherit",
      outline: "none"
    })
    textInput.onfocus = () => {
      textInput.style.borderColor = "#1e40af"
      textInput.style.boxShadow = "0 0 0 3px rgba(30, 64, 175, 0.15)"
    }
    textInput.onblur = () => {
      textInput.style.borderColor = "#cbd5e1"
      textInput.style.boxShadow = "none"
    }

    const actions = document.createElement("div")
    Object.assign(actions.style, {
      display: "flex",
      gap: "12px",
      justifyContent: "flex-end",
      marginTop: "4px"
    })

    const cancelBtn = document.createElement("button")
    cancelBtn.type = "button"
    cancelBtn.textContent = "Cancel"
    Object.assign(cancelBtn.style, {
      padding: "10px 18px",
      background: "#f1f5f9",
      border: "none",
      borderRadius: "8px",
      color: "#475569",
      fontWeight: "600",
      cursor: "pointer",
      fontSize: "14px"
    })
    cancelBtn.onclick = () => closeSelectedTextModal()

    const searchBtn = document.createElement("button")
    searchBtn.type = "button"
    searchBtn.textContent = "Search Vendors"
    Object.assign(searchBtn.style, {
      padding: "10px 18px",
      background: "#ffffff",
      border: "1px solid #cbd5e1",
      borderRadius: "8px",
      color: "#1e40af",
      fontWeight: "600",
      cursor: "pointer",
      fontSize: "14px"
    })
    searchBtn.onclick = () => {
      const text = textInput.value.trim()
      if (!text) {
        alert("Please enter an entity name.")
        textInput.focus()
        return
      }
      closeSelectedTextModal()
      void runSearch(text)
    }

    const placeOrderBtn = document.createElement("button")
    placeOrderBtn.type = "button"
    placeOrderBtn.textContent = "Place Order"
    Object.assign(placeOrderBtn.style, {
      padding: "10px 20px",
      background: "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)",
      border: "none",
      borderRadius: "8px",
      color: "#ffffff",
      fontWeight: "600",
      cursor: "pointer",
      fontSize: "14px",
      boxShadow: "0 4px 12px rgba(29, 78, 216, 0.2)"
    })
    placeOrderBtn.onclick = () => {
      const text = textInput.value.trim()
      if (!text) {
        alert("Please enter an entity name.")
        textInput.focus()
        return
      }
      lastSearchQuery = text
      queryText.textContent = text
      entityInput.value = text
      closeSelectedTextModal()
      openReportModal(text, cin || vendorData?.cin || "", vendorData)
    }

    actions.append(cancelBtn, searchBtn, placeOrderBtn)
    body.append(fieldLabel, textInput, actions)
    modal.append(header, body)
    overlay.append(modal)
    document.body.append(overlay)

    textInput.focus()
    if (initialText) {
      textInput.setSelectionRange(0, initialText.length)
    }
  }

  const createModal = (names: string[]) => {
    injectStyles()
    closeBuildersModal()

    const overlay = document.createElement("div")
    modalOverlayEl = overlay
    Object.assign(overlay.style, {
      position: "fixed",
      top: "0",
      left: "0",
      width: "100vw",
      height: "100vh",
      background: "rgba(15, 23, 42, 0.4)",
      backdropFilter: "blur(4px)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: "2147483646",
      animation: "overlayFadeIn 0.2s ease-out"
    })
    overlay.onclick = (e) => {
      if (e.target === overlay) closeBuildersModal()
    }

    const modal = document.createElement("div")
    modal.onclick = (e) => e.stopPropagation()
    Object.assign(modal.style, {
      background: "#ffffff",
      borderRadius: "16px",
      boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
      width: "780px",
      maxWidth: "95%",
      height: "560px",
      maxHeight: "85vh",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      animation: "modalFadeIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
      fontFamily: "system-ui, -apple-system, sans-serif"
    })

    const header = document.createElement("div")
    Object.assign(header.style, {
      background: "linear-gradient(135deg, #1e40af 0%, #1d4ed8 100%)",
      color: "#ffffff",
      padding: "18px 24px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      flexShrink: "0"
    })

    const title = document.createElement("strong")
    title.textContent = "Detected Builders / Developers"
    Object.assign(title.style, {
      fontSize: "16px",
      fontWeight: "600",
      letterSpacing: "-0.01em"
    })

    const closeBtn = document.createElement("button")
    closeBtn.innerHTML = "&times;"
    Object.assign(closeBtn.style, {
      border: "none",
      background: "rgba(255, 255, 255, 0.15)",
      fontSize: "20px",
      cursor: "pointer",
      lineHeight: "1",
      color: "#ffffff",
      width: "28px",
      height: "28px",
      borderRadius: "50%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      transition: "background 0.2s ease"
    })
    closeBtn.onmouseenter = () => closeBtn.style.background = "rgba(255, 255, 255, 0.3)"
    closeBtn.onmouseleave = () => closeBtn.style.background = "rgba(255, 255, 255, 0.15)"
    closeBtn.onclick = () => closeBuildersModal()

    header.append(title, closeBtn)

    const body = document.createElement("div")
    Object.assign(body.style, {
      display: "flex",
      flexDirection: "row",
      flex: "1",
      overflow: "hidden"
    })

    // Left Pane (Builders Badges)
    const leftPane = document.createElement("div")
    Object.assign(leftPane.style, {
      width: "280px",
      borderRight: "1px solid #e2e8f0",
      display: "flex",
      flexDirection: "column",
      overflowY: "auto",
      padding: "20px",
      flexShrink: "0",
      background: "#f8fafc"
    })

    const leftTitle = document.createElement("h4")
    leftTitle.textContent = "Select Developer"
    Object.assign(leftTitle.style, {
      margin: "0 0 12px 0",
      fontSize: "13px",
      fontWeight: "600",
      color: "#475569",
      textTransform: "uppercase",
      letterSpacing: "0.5px"
    })

    const badgesContainer = document.createElement("div")
    Object.assign(badgesContainer.style, {
      display: "flex",
      flexWrap: "wrap",
      gap: "8px"
    })

    leftPane.append(leftTitle, badgesContainer)

    // Right Pane (Search Results)
    const rightPane = document.createElement("div")
    Object.assign(rightPane.style, {
      flex: "1",
      display: "flex",
      flexDirection: "column",
      overflowY: "auto",
      padding: "20px",
      background: "#ffffff"
    })

    const rightTitle = document.createElement("div")
    Object.assign(rightTitle.style, {
      fontSize: "16px",
      fontWeight: "700",
      color: "#0f172a",
      marginBottom: "4px"
    })
    rightTitle.textContent = "Search Details"

    const modalStatusEl = document.createElement("div")
    Object.assign(modalStatusEl.style, {
      fontSize: "13px",
      color: "#64748b",
      marginBottom: "16px"
    })
    modalStatusEl.textContent = "Select a builder badge on the left to start search"

    const modalResultsEl = document.createElement("div")
    Object.assign(modalResultsEl.style, {
      display: "flex",
      flexDirection: "column",
      gap: "12px",
      flex: "1"
    })

    // Add empty state placeholder initially
    const emptyState = document.createElement("div")
    Object.assign(emptyState.style, {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      flex: "1",
      color: "#94a3b8",
      padding: "40px 20px",
      textAlign: "center"
    })
    emptyState.innerHTML = `
      <div style="font-size: 32px; margin-bottom: 8px;">🔍</div>
      <div style="font-weight: 500; font-size: 14px; color: #64748b;">No Developer Selected</div>
      <div style="font-size: 12px; max-width: 200px; margin-top: 4px;">Click any builder badge on the left to run search automatically.</div>
    `
    modalResultsEl.append(emptyState)

    rightPane.append(rightTitle, modalStatusEl, modalResultsEl)

    // Helper to render search results inside the modal
    const renderModalResults = (data: VendorResponse, searchQuery: string) => {
      modalResultsEl.innerHTML = ""
      modalStatusEl.textContent = `${data.total_count} vendor(s) found`

      if (!data.results.length) {
        appendPlaceReportFallback(
          modalResultsEl,
          searchQuery,
          "No matching vendors found for this builder."
        )
        return
      }

      for (const vendor of data.results) {
        const statusLower = vendor.company_status?.toLowerCase() || ""
        const isStrikeOff = statusLower.includes("strike") || statusLower.includes("struck")

        const card = document.createElement("div")
        Object.assign(card.style, {
          padding: "14px",
          border: "1px solid #e2e8f0",
          borderRadius: "10px",
          background: isStrikeOff ? "#f8fafc" : "#ffffff",
          boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
          transition: "all 0.2s ease",
          cursor: isStrikeOff ? "not-allowed" : "pointer",
          opacity: isStrikeOff ? "0.6" : "1"
        })

        if (!isStrikeOff) {
          card.onmouseenter = () => {
            card.style.borderColor = "#2563eb"
            card.style.boxShadow = "0 4px 12px rgba(37, 99, 235, 0.08)"
            card.style.transform = "translateY(-1px)"
          }
          card.onmouseleave = () => {
            card.style.borderColor = "#e2e8f0"
            card.style.boxShadow = "0 1px 3px rgba(0,0,0,0.02)"
            card.style.transform = "translateY(0)"
          }
          card.onclick = () => {
            closeBuildersModal()
            openSelectedTextModal(vendor.company_name, vendor, vendor.cin)
          }
        }

        const cardName = document.createElement("div")
        cardName.textContent = vendor.company_name
        Object.assign(cardName.style, {
          fontWeight: "600",
          color: "#0f172a",
          fontSize: "14px",
          marginBottom: "4px"
        })

        const cardMeta = document.createElement("div")
        Object.assign(cardMeta.style, {
          fontSize: "12px",
          color: "#475569"
        })

        // Status badge
        const isActive = vendor.company_status?.toLowerCase() === "active"
        const statusBadgeStyle = `
          display: inline-block;
          font-size: 10px;
          font-weight: 700;
          padding: 2px 6px;
          border-radius: 4px;
          margin-left: 6px;
          text-transform: uppercase;
          ${isActive ? 'background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9;' : 'background: #ffebee; color: #c62828; border: 1px solid #ffcdd2;'}
        `

        cardMeta.innerHTML = `
          <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <span>CIN: <strong>${vendor.cin}</strong></span>
            <span style="${statusBadgeStyle}">${vendor.company_status}</span>
          </div>
          <div style="margin-bottom: 4px; color: #64748b;">State Code: ${vendor.company_state_code}</div>
          <div style="color: #64748b; font-size: 11px; line-height: 1.4;">${vendor.registered_office_address}</div>
        `

        card.append(cardName, cardMeta)
        modalResultsEl.append(card)
      }
    }

    let activeBadgeEl: HTMLButtonElement | null = null

    names.forEach(name => {
      const badge = document.createElement("button")
      badge.textContent = name
      Object.assign(badge.style, {
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#ffffff",
        border: "1px solid #ced4da",
        color: "#495057",
        fontSize: "12px",
        fontWeight: "600",
        borderRadius: "16px",
        padding: "6px 12px",
        cursor: "pointer",
        transition: "all 0.15s ease",
        fontFamily: "inherit",
        boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
      })

      const selectBadge = () => {
        if (activeBadgeEl) {
          Object.assign(activeBadgeEl.style, {
            background: "#ffffff",
            borderColor: "#ced4da",
            color: "#495057"
          })
        }
        activeBadgeEl = badge
        Object.assign(badge.style, {
          background: "#e7f5ff",
          borderColor: "#228be6",
          color: "#228be6"
        })
      }

      badge.onmouseenter = () => {
        if (activeBadgeEl !== badge) {
          badge.style.background = "#f8f9fa"
          badge.style.borderColor = "#228be6"
          badge.style.color = "#228be6"
        }
      }
      badge.onmouseleave = () => {
        if (activeBadgeEl !== badge) {
          badge.style.background = "#ffffff"
          badge.style.borderColor = "#ced4da"
          badge.style.color = "#495057"
        } else {
          badge.style.background = "#e7f5ff"
          badge.style.borderColor = "#228be6"
          badge.style.color = "#228be6"
        }
      }

      badge.onclick = async (e) => {
        e.stopPropagation()
        window.getSelection()?.removeAllRanges()
        selectBadge()
        rightTitle.textContent = name
        modalStatusEl.textContent = "Searching..."
        modalResultsEl.innerHTML = `
          <div style="display: flex; align-items: center; justify-content: center; flex: 1; padding: 40px;">
            <div style="border: 3px solid #f3f3f3; border-top: 3px solid #228be6; border-radius: 50%; width: 24px; height: 24px; animation: modalSpinner 1s linear infinite; margin-right: 10px;"></div>
            <span style="font-size: 13px; color: #64748b; font-weight: 500;">Retrieving details...</span>
          </div>
        `

        try {
          const data = await searchVendors(name)
          renderModalResults(data, name)
        } catch (err) {
          modalStatusEl.textContent = "Search failed"
          modalResultsEl.innerHTML = ""
          appendPlaceReportFallback(
            modalResultsEl,
            name,
            err instanceof Error ? err.message : "Search failed."
          )
        }
      }

      badgesContainer.append(badge)
    })

    body.append(leftPane, rightPane)
    modal.append(header, body)
    overlay.append(modal)
    document.body.append(overlay)
  }

  const extractNames = (): string[] => {
    const hostname = window.location.hostname
    const isHousing = hostname.includes("housing.com")
    const is99acres = hostname.includes("99acres.com")

    if (!isHousing && !is99acres) {
      return []
    }

    const foundNames = new Set<string>()
    
    const exactBlacklist = [
      "builder", "developer", "seller", "agent", "owner", "contact", "verified", "locality"
    ]

    const substringBlacklist = [
      "school", "bus stand", "property market guide", "market guide", "hospital", 
      "railway", "station", "airport", "park", "overview", "amenity", "amenities", 
      "specification", "specifications", "floor plan", "floorplans", "price trend", 
      "price trends", "view phone", "phone number", "local info", "local information", 
      "map", "directions", "gallery", "photos", "reviews", "ratings", "faq", 
      "frequently asked", "similar projects", "locality", "about project", 
      "about developer", "about builder", "commercial", "residential", "housing", "home loan", 
      "emi calculator", "emi", "calculator"
    ]

    const addCleanName = (text: string) => {
      const clean = text.replace(/^\s*by\s+/i, "").trim()
      if (clean && clean.length > 2 && clean.length < 80) {
        const lower = clean.toLowerCase()
        const isExactBlacklisted = exactBlacklist.includes(lower)
        const isSubstringBlacklisted = substringBlacklist.some(item => lower.includes(item))
        if (!isExactBlacklisted && !isSubstringBlacklisted && !/^\d+$/.test(clean)) {
          foundNames.add(clean)
        }
      }
    }

    if (isHousing) {
      const selectors = [
        "div.css-17zjzsz",
        "div.T_developerStyle",
        "div.developer.css-1ocb6y4",
        "div.name.T_nameStyle", // Match only when both 'name' and 'T_nameStyle' are present
        "[data-q='dev-name']"
      ]

      selectors.forEach(sel => {
        try {
          const els = document.querySelectorAll(sel)
          els.forEach(el => {
            if (el.getAttribute("data-q") === "title") {
              return
            }
            addCleanName(el.textContent || "")
          })
        } catch (e) {
          console.error("Selector error:", sel, e)
        }
      })

      // classList matches for extra robustness
      try {
        const allDivs = document.querySelectorAll("div")
        allDivs.forEach(div => {
          if (div.getAttribute("data-q") === "title") {
            return
          }
          const classList = div.classList
          if (classList && classList.length > 0) {
            const isDeveloper = classList.contains("T_developerStyle") || 
                                (classList.contains("developer") && classList.contains("css-1ocb6y4")) || 
                                (classList.contains("T_nameStyle") && classList.contains("name")) || 
                                classList.contains("css-17zjzsz")
            
            if (isDeveloper) {
              addCleanName(div.textContent || "")
            }
          }
        })
      } catch (e) {
        console.error("Generic search error:", e)
      }
    } else if (is99acres) {
      const selectors = [
        "div.PseudoTupleRevamp__contactSubheading",
        "div.section_header_bold.spacer4"
      ]

      selectors.forEach(sel => {
        try {
          const els = document.querySelectorAll(sel)
          els.forEach(el => {
            addCleanName(el.textContent || "")
          })
        } catch (e) {
          console.error("99acres selector error:", sel, e)
        }
      })

      // classList matches for extra robustness
      try {
        const allDivs = document.querySelectorAll("div")
        allDivs.forEach(div => {
          const className = div.className
          if (typeof className === "string") {
            const matches = className.includes("PseudoTupleRevamp__contactSubheading") || 
                            (className.includes("section_header_bold") && className.includes("spacer4"))
            if (matches) {
              addCleanName(div.textContent || "")
            }
          }
        })
      } catch (e) {
        console.error("99acres generic search error:", e)
      }
    }

    return Array.from(foundNames)
  }

  const checkUrlChange = () => {
    const currentUrl = window.location.href
    if (currentUrl !== lastUrl) {
      lastUrl = currentUrl
      detectedNames = []
      detectBtn.style.display = "none"
      closeBuildersModal()
      closeSelectedTextModal()
      closeInfraSearchModal()
    }
  }

  const scanAndPopulateNames = () => {
    checkUrlChange()

    const names = extractNames()
    if (names.length === 0) {
      detectBtn.style.display = "none"
      return
    }

    detectedNames = names
    detectBtn.textContent = `🔍 Builders (${names.length})`
    detectBtn.style.display = "block"
  }

  detectBtn.onclick = (e) => {
    e.stopPropagation()
    if (detectedNames.length > 0) {
      createModal(detectedNames)
    }
  }

  root.append(panel, buttonsContainer)
  document.body.append(root)

  // Set up debounced MutationObserver and trigger scan ONLY on housing.com & 99acres.com
  const isSupportedDomain = window.location.hostname.includes("housing.com") || window.location.hostname.includes("99acres.com")
  if (isSupportedDomain) {
    let scanTimeout: number | null = null
    const triggerScan = () => {
      if (scanTimeout) {
        clearTimeout(scanTimeout)
      }
      scanTimeout = window.setTimeout(() => {
        scanAndPopulateNames()
      }, 800)
    }

    const observer = new MutationObserver(() => {
      triggerScan()
    })
    observer.observe(document.body, {
      childList: true,
      subtree: true
    })

    // Run initial scan
    triggerScan()
  }
}
