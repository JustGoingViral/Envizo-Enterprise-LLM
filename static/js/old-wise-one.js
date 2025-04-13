/**
 * Interactive Floating Pacman AI Assistant
 * A helpful, wise AI enterprise expert that provides guidance and assistance
 */

class OldWiseOne {
  constructor() {
    this.isVisible = false;
    this.isMinimized = false;
    this.messages = [];
    this.isRoaming = true;
    this.position = { x: 10, y: 10 }; // Start at top-left corner
    this.targetPosition = { x: 10, y: 10 };
    this.speed = 1; // Slower speed for a calmer movement along the edge
    this.characterSize = 60; // Size in pixels (approx 3 emojis stacked)
    this.is3DMode = true; // Enable 3D wandering mode
    this.currentDirection = 'right'; // Current movement direction
    this.gridSize = 30; // Size of virtual grid for movement

    // We've removed the dots scattered around screen, keeping only the Pacman character
    this.powerPelletActive = false; // Special power mode
    this.wisdomQuotes = [
      "Envizo AI Platform: where data privacy meets computational power.",
      "Multi-GPU infrastructure optimization is the cornerstone of Envizo AI Platform scalability.",
      "Envizo AI Platform implementations balance performance, cost, and governance.",
      "Data privacy and AI capabilities are not mutually exclusive with Envizo AI Platform.",
      "Envizo AI Platform success depends on centralized management with distributed access.",
      "Envizo AI Platform turns experimental technology into a business advantage.",
      "Envizo AI Platform requires both technical expertise and strategic vision.",
      "The future belongs to organizations that successfully implement Envizo AI Platform.",
      "True AI transformation comes from Envizo AI Platform with controlled access to powerful models."
    ];
    this.initialized = true;
    console.log('Old Wise One initialized');
    this.init();
    this.setupEventListeners(); // Added from edited code

    // Start the roaming animation
    this.startRoaming();
  }

  init() {
    this.createElements();
    
    // Added a welcome message but don't automatically show the chat
    this.addMessage('Envizo AI Assistant', 'Greetings! I am your Envizo AI enterprise expert, here to guide you through the Envizo AI Platform. How may I assist you today?');
  }

  createElements() {
    // Create main container
    this.container = document.createElement('div');
    this.container.className = 'old-wise-one-container';
    this.container.style.display = 'none';

    // Create header with avatar and controls
    this.header = document.createElement('div');
    this.header.className = 'old-wise-one-header';

    // Envizo AI avatar
    this.avatar = document.createElement('div');
    this.avatar.className = 'old-wise-one-avatar';
    this.avatar.innerHTML = '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">' +
      '<circle cx="50" cy="50" r="40" fill="#00AB55" />' + // Updated brand color
      '<path d="M30,30 L50,20 L70,30 L70,50 L50,60 L30,50 Z" fill="#fff" />' + // Hexagon shape
      '<circle cx="50" cy="40" r="10" fill="#00AB55" />' + // Center circle
      '<path d="M38,52 L62,52 L50,70 Z" fill="#fff" />' + // Bottom triangle
      '</svg>';

    // Title
    this.title = document.createElement('div');
    this.title.className = 'old-wise-one-title';
    this.title.innerText = 'Envizo AI Assistant';

    // Controls
    this.controls = document.createElement('div');
    this.controls.className = 'old-wise-one-controls';

    this.minimizeBtn = document.createElement('button');
    this.minimizeBtn.className = 'old-wise-one-btn minimize';
    this.minimizeBtn.innerHTML = '−';
    this.minimizeBtn.title = 'Minimize';

    this.closeBtn = document.createElement('button');
    this.closeBtn.className = 'old-wise-one-btn close';
    this.closeBtn.innerHTML = '×';
    this.closeBtn.title = 'Close';

    this.controls.appendChild(this.minimizeBtn);
    this.controls.appendChild(this.closeBtn);

    // Assemble header
    this.header.appendChild(this.avatar);
    this.header.appendChild(this.title);
    this.header.appendChild(this.controls);

    // Create content area
    this.content = document.createElement('div');
    this.content.className = 'old-wise-one-content';

    // Messages container
    this.messagesContainer = document.createElement('div');
    this.messagesContainer.className = 'old-wise-one-messages';

    // Input area
    this.inputArea = document.createElement('div');
    this.inputArea.className = 'old-wise-one-input-area';

    this.input = document.createElement('textarea');
    this.input.className = 'old-wise-one-input';
    this.input.placeholder = 'Ask Envizo AI...';
    this.input.rows = 1;

    this.sendBtn = document.createElement('button');
    this.sendBtn.className = 'old-wise-one-send-btn';
    this.sendBtn.innerHTML = '<svg viewBox="0 0 24 24" width="24" height="24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" fill="currentColor"></path></svg>';
    this.sendBtn.title = 'Send';

    this.inputArea.appendChild(this.input);
    this.inputArea.appendChild(this.sendBtn);

    // Assemble content
    this.content.appendChild(this.messagesContainer);
    this.content.appendChild(this.inputArea);

    // Create minimized avatar for when the chat is minimized
    this.minimizedAvatar = document.createElement('div');
    this.minimizedAvatar.className = 'old-wise-one-minimized';
    this.minimizedAvatar.style.display = 'none';
    this.minimizedAvatar.innerHTML = this.avatar.innerHTML;

    // Assemble main container
    this.container.appendChild(this.header);
    this.container.appendChild(this.content);

    // Add to document
    document.body.appendChild(this.container);
    document.body.appendChild(this.minimizedAvatar);

    // Add styles
    this.addStyles();
  }

  addStyles() {
    const styleEl = document.createElement('style');
    styleEl.textContent = `
      .old-wise-one-container {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 350px;
        height: 450px;
        background-color: #222;
        border-radius: 12px;
        box-shadow: 0 5px 25px rgba(0, 0, 0, 0.3);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        z-index: 1000;
        transition: all 0.3s ease;
        color: #f9f9f9;
      }
      
      .old-wise-one-header {
        display: flex;
        align-items: center;
        padding: 12px;
        background-color: #2c2c2c;
        cursor: move;
        user-select: none;
      }
      
      .old-wise-one-avatar {
        width: 40px;
        height: 40px;
        margin-right: 12px;
      }
      
      .old-wise-one-title {
        flex: 1;
        font-size: 18px;
        font-weight: 500;
      }
      
      .old-wise-one-controls {
        display: flex;
      }
      
      .old-wise-one-btn {
        background: none;
        border: none;
        color: #ccc;
        font-size: 20px;
        margin-left: 5px;
        cursor: pointer;
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: background-color 0.2s;
      }
      
      .old-wise-one-btn:hover {
        background-color: rgba(255, 255, 255, 0.1);
      }
      
      .old-wise-one-btn.close:hover {
        background-color: rgba(255, 0, 0, 0.2);
      }
      
      .old-wise-one-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      
      .old-wise-one-messages {
        flex: 1;
        overflow-y: auto;
        padding: 15px;
      }
      
      .old-wise-one-message {
        margin-bottom: 15px;
        max-width: 85%;
      }
      
      .old-wise-one-message.buddha {
        align-self: flex-start;
      }
      
      .old-wise-one-message.user {
        align-self: flex-end;
        margin-left: auto;
      }
      
      .old-wise-one-message-bubble {
        padding: 10px 14px;
        border-radius: 18px;
        display: inline-block;
        word-break: break-word;
      }
      
      .old-wise-one-message.buddha .old-wise-one-message-bubble {
        background-color: #3a3a3a;
        border-bottom-left-radius: 5px;
      }
      
      .old-wise-one-message.user .old-wise-one-message-bubble {
        background-color: #007bff;
        border-bottom-right-radius: 5px;
      }
      
      .old-wise-one-message-sender {
        font-size: 12px;
        margin-bottom: 3px;
        opacity: 0.8;
      }
      
      .old-wise-one-input-area {
        display: flex;
        padding: 10px;
        background-color: #2c2c2c;
        align-items: flex-end;
      }
      
      .old-wise-one-input {
        flex: 1;
        border: none;
        background-color: #3a3a3a;
        color: #f9f9f9;
        border-radius: 18px;
        padding: 10px 15px;
        resize: none;
        max-height: 120px;
        outline: none;
        transition: background-color 0.2s;
      }
      
      .old-wise-one-input:focus {
        background-color: #444;
      }
      
      .old-wise-one-send-btn {
        background: none;
        border: none;
        color: #007bff;
        margin-left: 8px;
        cursor: pointer;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: background-color 0.2s;
      }
      
      .old-wise-one-send-btn:hover {
        background-color: rgba(0, 123, 255, 0.1);
      }
      
      .old-wise-one-minimized {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 60px;
        height: 60px;
        background-color: #222;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        z-index: 1000;
        transition: transform 0.3s ease;
      }
      
      .old-wise-one-minimized:hover {
        transform: scale(1.1);
      }
      
      .old-wise-one-minimized svg {
        width: 45px;
        height: 45px;
      }
      
      /* Wisdom quote bubble */
      .wisdom-quote-bubble {
        position: absolute;
        bottom: 70px;
        right: 70px;
        background-color: #2c2c2c;
        color: #f9f9f9;
        padding: 10px 15px;
        border-radius: 10px;
        max-width: 250px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        font-style: italic;
        z-index: 999;
        animation: fadeIn 0.5s;
      }
      
      .wisdom-quote-bubble:after {
        content: '';
        position: absolute;
        bottom: -10px;
        right: 20px;
        border-width: 10px 10px 0;
        border-style: solid;
        border-color: #2c2c2c transparent;
      }
      
      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
    `;
    document.head.appendChild(styleEl);
  }

  setupEventListeners() {
    // Toggle visibility when clicking the x button
    this.closeBtn.addEventListener('click', () => this.toggleVisibility());

    // Toggle minimized state
    this.minimizeBtn.addEventListener('click', () => this.toggleMinimized());

    // Show the chat when clicking the minimized avatar
    this.minimizedAvatar.addEventListener('click', () => this.toggleMinimized());

    // Random wisdom quotes on hover
    this.minimizedAvatar.addEventListener('mouseenter', () => this.showRandomWisdomQuote());
    this.minimizedAvatar.addEventListener('mouseleave', () => this.hideWisdomQuote());

    // Send message when clicking send button or pressing Enter
    this.sendBtn.addEventListener('click', () => this.handleUserMessage());
    this.input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleUserMessage();
      }
    });

    // Make the OldWiseOne draggable
    this.enableDragging();

    // Adjust textarea height as user types
    this.input.addEventListener('input', () => {
      this.input.style.height = 'auto';
      this.input.style.height = Math.min(this.input.scrollHeight, 120) + 'px';
    });
  }

  enableDragging() {
    let offsetX, offsetY, isDragging = false;

    const dragStart = (e) => {
      // Only allow dragging from the header
      if (e.target.closest('.old-wise-one-controls')) return;

      isDragging = true;
      offsetX = e.clientX - this.container.getBoundingClientRect().left;
      offsetY = e.clientY - this.container.getBoundingClientRect().top;

      // Add a temporary event listeners for dragging
      document.addEventListener('mousemove', drag);
      document.addEventListener('mouseup', dragEnd);
    };

    const drag = (e) => {
      if (!isDragging) return;

      // Calculate the new position
      const x = e.clientX - offsetX;
      const y = e.clientY - offsetY;

      // Update position
      this.container.style.left = `${Math.max(0, x)}px`;
      this.container.style.right = 'auto';
      this.container.style.top = `${Math.max(0, y)}px`;
      this.container.style.bottom = 'auto';
    };

    const dragEnd = () => {
      isDragging = false;
      document.removeEventListener('mousemove', drag);
      document.removeEventListener('mouseup', dragEnd);
    };

    this.header.addEventListener('mousedown', dragStart);
  }

  toggleVisibility() {
    this.isVisible = !this.isVisible;

    if (this.isVisible) {
      // When making visible
      if (this.isMinimized) {
        if (this.is3DMode) {
          // In 3D mode, hide chat window but keep 3D character
          this.container.style.display = 'none';
          if (this.roamingCharacter) {
            this.roamingCharacter.style.display = 'block';
          } else {
            // Start 3D roaming if it's not already started
            this.startRoaming();
          }
        } else {
          // In regular mode, show minimized avatar
          this.minimizedAvatar.style.display = 'flex';
          this.container.style.display = 'none';
        }
      } else {
        // Showing full chat window
        this.minimizedAvatar.style.display = 'none';
        this.container.style.display = 'flex';

        // Stop 3D roaming when full chat is shown
        if (this.is3DMode && this.roamingCharacter) {
          this.roamingCharacter.style.display = 'none';
        }
      }
      this.hideWisdomQuote();
    } else {
      // When hiding completely
      this.container.style.display = 'none';
      this.minimizedAvatar.style.display = 'none';

      // If in 3D mode, still show the character
      if (this.is3DMode) {
        if (this.roamingCharacter) {
          this.roamingCharacter.style.display = 'block';
        } else {
          this.startRoaming();
        }
      }

      this.hideWisdomQuote();
    }
  }

  toggleMinimized() {
    this.isMinimized = !this.isMinimized;

    if (this.isMinimized) {
      // When minimizing
      this.container.style.display = 'none';

      if (this.is3DMode) {
        // In 3D mode, show the roaming character
        if (this.roamingCharacter) {
          this.roamingCharacter.style.display = 'block';
        } else {
          this.startRoaming();
        }
      } else {
        // In regular mode, show the minimized avatar
        this.minimizedAvatar.style.display = 'flex';
      }
    } else {
      // When maximizing
      this.container.style.display = 'flex';
      this.minimizedAvatar.style.display = 'none';

      // Hide the 3D character when showing full chat
      if (this.is3DMode && this.roamingCharacter) {
        this.roamingCharacter.style.display = 'none';
      }

      this.hideWisdomQuote();

      // Focus on the input when maximizing
      setTimeout(() => this.input.focus(), 100);
    }
  }

  showRandomWisdomQuote() {
    // Remove any existing quote bubble
    this.hideWisdomQuote();

    // Get a random wisdom quote
    const quote = this.wisdomQuotes[Math.floor(Math.random() * this.wisdomQuotes.length)];

    // Create and append the quote bubble
    const bubble = document.createElement('div');
    bubble.className = 'wisdom-quote-bubble';
    bubble.textContent = quote;
    bubble.id = 'wisdom-quote-bubble';

    // Position the bubble correctly depending on the context
    if (this.is3DMode && this.roamingCharacter && this.roamingCharacter.style.display !== 'none') {
      // For 3D mode, position relative to the roaming character
      document.body.appendChild(bubble);
      const charRect = this.roamingCharacter.getBoundingClientRect();

      bubble.style.position = 'absolute';
      bubble.style.left = charRect.right + 'px';
      bubble.style.top = (charRect.top - bubble.offsetHeight / 2) + 'px';

      // Reposition if off-screen
      setTimeout(() => {
        const bubbleRect = bubble.getBoundingClientRect();
        if (bubbleRect.right > window.innerWidth) {
          bubble.style.left = (charRect.left - bubbleRect.width) + 'px';
        }
        if (bubbleRect.top < 0) {
          bubble.style.top = '10px';
        }
      }, 0);
    } else {
      // For minimized mode, position relative to the minimized avatar
      document.body.appendChild(bubble);

      // Default position from CSS will be used (bottom: 70px, right: 70px)
    }

    // Set a timeout to remove the quote after some time
    this.quoteTimeout = setTimeout(() => this.hideWisdomQuote(), 5000);
  }

  hideWisdomQuote() {
    clearTimeout(this.quoteTimeout);
    const bubble = document.getElementById('wisdom-quote-bubble');
    if (bubble) bubble.remove();
  }

  handleUserMessage() {
    const message = this.input.value.trim();
    if (!message) return;

    // Add the user message
    this.addMessage('You', message, 'user');

    // Clear the input and reset its height
    this.input.value = '';
    this.input.style.height = 'auto';

    // Process the message and generate a response
    this.processUserMessage(message);
  }

  processUserMessage(message) {
    // Enhanced keyword-based responses with enterprise LLM expertise
    let response;
    const messageLower = message.toLowerCase();

    // Check for greetings
    if (/hello|hi|hey|greetings/i.test(messageLower)) {
      response = "Greetings, seeker. How may I illuminate your path today? Ask me about our Enterprise LLM Platform, on-premises deployments, or integration capabilities.";
    }

    // Enterprise LLM Deployment scenarios
    else if (/deploy|deployment|infrastructure|on-premises|on-prem|server|hosting/i.test(messageLower)) {
      response = "Our Enterprise LLM Platform excels in on-premises deployments. We recommend a dedicated server with 24GB+ VRAM GPUs (such as NVIDIA A10/A100/H100) for optimal performance with models like Mistral-7B or LLaMA-3. The platform manages multi-GPU resources efficiently, load-balancing requests across server nodes while maintaining data privacy within your organization's infrastructure. Would you like details on our deployment architecture or hardware requirements?";
    }

    // BI Integration scenarios
    else if (/bi|business intelligence|focal|focal bi|integration|connect|tableau|power bi/i.test(messageLower)) {
      response = "Our platform seamlessly integrates with Focal BI and other business intelligence platforms through secure API endpoints. Your BI system can submit natural language queries to our LLM server, which processes them and returns results without requiring any model installations on end-user workstations. All processing happens centrally, ensuring consistent performance while maintaining your data privacy requirements. The Analytics dashboard shows you detailed usage metrics across your organization.";
    }

    // Hardware requirements
    else if (/hardware|gpu|ram|vram|requirements|specs|nvidia|server specs/i.test(messageLower)) {
      response = "For enterprise deployments, we recommend the following minimum specifications: A server with NVIDIA A10 (24GB VRAM) or better GPU, 64GB system RAM, 1TB NVMe storage, and Ubuntu 22.04 LTS. For production environments handling multiple concurrent users, consider multi-GPU setups with A100 (40/80GB) or H100 GPUs, which our load balancer will utilize efficiently. The platform monitors GPU utilization in real-time, as you can see in the Analytics dashboard.";
    }

    // Multi-site deployment and synchronization
    else if (/multi-site|multiple locations|synchronize|synchronization|global|distributed/i.test(messageLower)) {
      response = "Our platform supports distributed deployments across multiple sites with centralized management. You can deploy LLM servers in different geographical locations while maintaining synchronization of models, fine-tuning data, and analytics. This approach reduces latency for global teams while ensuring consistent model behavior and centralized governance. Would you like to learn more about our distributed architecture?";
    }

    // Fine-tuning capabilities
    else if (/fine-tuning|fine tune|custom model|training|customize|adapt|domain specific|specialized/i.test(messageLower)) {
      response = "The platform's fine-tuning capabilities allow you to adapt pre-trained models to your organization's specific data, terminology, and use cases. You can upload custom datasets through the Fine-Tuning interface, configure hyperparameters, and monitor training progress. This results in models that better understand your industry's context, reducing hallucinations and improving accuracy. Fine-tuned models are automatically made available through the same API endpoints.";
    }

    // Data privacy and security
    else if (/privacy|security|confidential|sensitive|data leakage|compliance|secure/i.test(messageLower)) {
      response = "Data privacy is ensured through our on-premises approach - all data remains within your infrastructure without calling external APIs. The platform supports role-based access controls, detailed audit logging, and encrypted communications. All inference requests and responses are logged with user attribution for compliance purposes. For highly sensitive deployments, the system can operate in air-gapped environments with no external network dependencies.";
    }

    // Check for questions about analytics
    else if (/analytics|metrics|monitoring|dashboard|usage|statistics|performance/i.test(messageLower)) {
      response = "The Analytics dashboard provides comprehensive insights into your LLM infrastructure. You can monitor GPU utilization across server nodes, track query volumes by user/department, analyze response times, and identify usage patterns. The system maintains historical data for trend analysis and capacity planning. This helps you optimize resource allocation and identify opportunities for model improvements based on actual usage patterns.";
    }

    // Check for advanced deployment scenario specifically for Focal BI
    else if (/focal bi integration|dedicated server|centralized|workstation|api infrastructure/i.test(messageLower) ||
            messageLower.includes("on-premises server") && messageLower.includes("business intelligence")) {
      response = "For your scenario of deploying a dedicated on-premises LLM server integrated with Focal BI, our platform is the ideal solution. The architecture would consist of: 1) A central server with 24GB+ VRAM GPUs running our platform, 2) The existing Focal BI system connecting via secure API endpoints, 3) Employee workstations accessing AI capabilities through Focal BI without local model installation. This setup ensures data privacy, consistent performance, reduced workstation requirements, and centralized management. Would you like me to explain the implementation steps?";
    }

    // Implementation steps for Focal BI integration
    else if (/implementation steps|how to implement|setup guide|setup process|installation/i.test(messageLower)) {
      response = "Implementing the platform with Focal BI involves these key steps: 1) Provision a server meeting our hardware requirements, 2) Install our platform using the deployment guide, 3) Configure the GPU resources and load balancing settings, 4) Set up user authentication and API keys, 5) Configure the Focal BI connector to use our API endpoints, 6) Test the integration with sample queries, and 7) Monitor performance through our Analytics dashboard. Our implementation team can guide you through each step for a smooth deployment.";
    }

    // Check for questions about the application
    else if (/what|how|where|when|why|who|explain|tell me about/i.test(messageLower) &&
            /application|app|platform|system|llm|dashboard|feature|work/i.test(messageLower)) {
      response = "The Envizo AI Platform is a comprehensive solution for organizations seeking to leverage AI language models internally. Key features include: 1) Multi-GPU server management with intelligent load balancing, 2) Model fine-tuning for domain-specific knowledge, 3) Semantic caching for performance optimization, 4) Detailed analytics and monitoring, 5) Seamless integration with business systems through our Business Intelligence Integration, and 6) Enterprise-grade security and access controls. All processing remains within your infrastructure, ensuring data privacy while providing powerful AI capabilities to your entire organization.";
    }

    // Check for help requests
    else if (/help|guide|assist|support/i.test(messageLower)) {
      response = "I'm here to guide you through the Envizo AI Platform. You can navigate through different sections using the navigation menu. The dashboard provides system overview, Analytics offers usage insights, and Fine-Tuning allows model customization. For deployment assistance, explore the Admin section. What specific aspect would you like help with today? I can provide guidance on deployment architecture, hardware requirements, Business Intelligence integration, or usage scenarios.";
    }

    // Check for gratitude
    else if (/thank|thanks|grateful|appreciate/i.test(messageLower)) {
      response = "You are most welcome. I'm here to provide clarity on your AI infrastructure journey. Feel free to return anytime you need insights on enterprise LLM deployments or optimizing your implementation.";
    }

    // Check for questions about AI expertise
    else if (/ai expertise|ai experience|enterprise|explain|experience|credentials/i.test(messageLower)) {
      response = "As an AI enterprise expert, I've guided numerous organizations through their LLM deployment journeys. The Envizo AI Platform brings clarity to your organization's AI strategy - removing complexity and providing a clear path forward with on-premises language models that maintain data privacy while maximizing infrastructure efficiency.";
    }

    // Information about the founder
    else if (/founder|ceo|leadership|who|company|history|created|started/i.test(messageLower)) {
      response = "Envizo AI was co-founded by Benjamin (Ben) Bohman, who serves as the COO. Ben brings nearly 3 decades of technology expertise to the AI industry. With a background in psychology and organizational behavior, he approaches AI development with a human-centered perspective. During his 13-year IT leadership at an international printing company, he revolutionized manufacturing operations through innovative technology solutions that were later adopted by major organizations like the NFL and Anheuser-Busch. Ben's vision focuses on helping companies leverage their internal data more effectively through AI integration while maintaining ethical standards.";
    }

    // Specific information about Ben Bohman
    else if (/ben|benjamin|bohman/i.test(messageLower)) {
      response = "Benjamin (Ben) Bohman is the co-founder and COO of Envizo AI. His career exemplifies the intersection of technology leadership and human-centered design. With nearly 3 decades of technology expertise, Ben has a strong foundation in psychology and organizational behavior. During his 13-year tenure as an IT leader for an international printing company, he revolutionized manufacturing operations through innovative technology solutions that were adopted by industry giants including the NFL and Anheuser-Busch. Ben has a bachelor's degree in psychology and is pursuing a master's in organizational psychology, allowing him to bridge the gap between technical solutions and human needs. His passion lies in helping companies leverage their internal data more effectively through AI integration, enhancing organizational decision-making processes, and ensuring AI solutions maintain ethical standards while driving innovation.";
    }

    // Default response with enterprise LLM wisdom
    else {
      const enterpriseWisdom = [
        "The journey to AI transformation begins with a single step: deploying your first on-premises LLM server. Our platform makes this journey smooth and rewarding.",
        "Just as a river finds many paths to the ocean, our platform offers multiple ways to integrate AI capabilities into your existing business systems.",
        "True enterprise AI wisdom comes from understanding both the capabilities and limitations of language models. Our platform helps you maximize strengths while mitigating weaknesses.",
        "The most powerful AI implementations are those that align perfectly with organizational needs. Our platform's flexibility allows it to adapt to your specific requirements.",
        "Like a skilled gardener who knows which plants thrive in which conditions, our platform helps you deploy the right models for the right use cases.",
        "In the world of enterprise AI, the path of centralized deployment often leads to the greatest efficiency and governance. Our platform embodies this principle.",
        "The wise organization builds AI infrastructure that balances innovation with security, performance with cost-efficiency. This balance is at the core of our platform design."
      ];
      response = enterpriseWisdom[Math.floor(Math.random() * enterpriseWisdom.length)];
    }

    // Add a slight delay to make it feel more natural
    setTimeout(() => {
      this.addMessage('Envizo AI Assistant', response);
    }, 1000);
  }

  addMessage(sender, text, type = 'buddha') {
    // Create message container
    const messageEl = document.createElement('div');
    messageEl.className = `old-wise-one-message ${type}`;

    // Create sender label
    const senderEl = document.createElement('div');
    senderEl.className = 'old-wise-one-message-sender';
    senderEl.textContent = sender;

    // Create message bubble
    const bubbleEl = document.createElement('div');
    bubbleEl.className = 'old-wise-one-message-bubble';
    bubbleEl.textContent = text;

    // Assemble message
    messageEl.appendChild(senderEl);
    messageEl.appendChild(bubbleEl);

    // Add to messages container
    this.messagesContainer.appendChild(messageEl);

    // Scroll to bottom
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

    // Store in messages array
    this.messages.push({ sender, text, type });
  }

  // 3D Roaming Character Methods

  startRoaming() {
    // Create the 3D wandering character
    this.create3DCharacter();

    // Set new random target position
    this.setRandomTarget();

    // Start animation loop
    this.animationFrame = requestAnimationFrame(() => this.animateRoaming());
  }

  createScoreDisplay() {
    // No longer needed since we've removed score display
  }

  updateScore() {
    // No longer needed since we've removed score display
  }

  createInteractiveDots() {
    // No longer needed since we've removed interactive dots
  }

  createSingleDot(maxX, maxY, buffer) {
    // No longer needed since we've removed interactive dots
  }

  createPowerPellet(maxX, maxY, buffer) {
    // No longer needed since we've removed interactive dots
  }

  clearInteractiveDots() {
    // This method is now empty since we've removed interactive dots
  }

  startCollisionDetection() {
    // No longer needed since we've removed interactive dots
  }

  checkCollisions() {
    // No longer needed since we've removed interactive dots
  }

  eatDot(index, dot) {
    // No longer needed since we've removed interactive dots
  }

  activatePowerMode() {
    // No longer needed since we've removed power pellets
  }

  create3DCharacter() {
    // Create 3D character that will roam around
    this.roamingCharacter = document.createElement('div');
    this.roamingCharacter.className = 'old-wise-one-3d-character';

    // Create Pacman SVG with 3 dots in front of it and a "Click me" label
    this.roamingCharacter.innerHTML = `
      <div class="character-3d-container">
        <div class="pacman-container">
          <!-- Pacman -->
          <svg class="pacman" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="40" fill="#FFFF00" />
            <path class="pacman-mouth" d="M50,50 L90,20 A40,40 0 0,1 90,80 Z" fill="#000">
              <animate 
                attributeName="d" 
                values="M50,50 L90,20 A40,40 0 0,1 90,80 Z;M50,50 L90,45 A40,40 0 0,1 90,55 Z;M50,50 L90,20 A40,40 0 0,1 90,80 Z" 
                dur="0.5s"
                repeatCount="indefinite" />
            </path>
          </svg>

          <!-- The 3 dots in front -->
          <div class="pacman-dots">
            <div class="pacman-dot"></div>
            <div class="pacman-dot"></div>
            <div class="pacman-dot"></div>
          </div>
        </div>
        <!-- Click me label -->
        <div class="click-me-label">Click me</div>
      </div>
    `;

    // Add click event to open chat when 3D character is clicked
    this.roamingCharacter.addEventListener('click', () => {
      console.log("Pacman clicked - opening chat");
      this.isMinimized = false;
      this.isVisible = true;

      // Force display the chat window
      this.container.style.display = 'flex';

      // Hide the Pacman
      if (this.roamingCharacter) {
        this.roamingCharacter.style.display = 'none';
      }

      // Make sure minimized avatar is hidden
      this.minimizedAvatar.style.display = 'none';
    });

    // Position the character
    this.updateCharacterPosition();

    // Add to document body
    document.body.appendChild(this.roamingCharacter);

    // Add 3D character styles
    this.add3DCharacterStyles();
  }

  add3DCharacterStyles() {
    const styleEl = document.createElement('style');
    styleEl.textContent = `
      .old-wise-one-3d-character {
        position: fixed;
        width: ${this.characterSize * 2.5}px; /* Make wider to accommodate dots */
        height: ${this.characterSize}px;
        pointer-events: auto;
        cursor: pointer;
        z-index: 999;
        transition: transform 0.3s ease;
      }
      
      .old-wise-one-3d-character:hover {
        transform: scale(1.1);
      }
      
      .character-3d-container {
        width: 100%;
        height: 100%;
        position: relative;
      }
      
      .pacman-container {
        display: flex;
        align-items: center;
        height: 100%;
        position: relative;
      }
      
      .pacman {
        width: ${this.characterSize}px;
        height: ${this.characterSize}px;
        filter: drop-shadow(0 3px 5px rgba(0, 0, 0, 0.3));
      }
      
      .pacman-mouth {
        /* Animation now handled by SVG animate element */
      }
      
      .pacman-dots {
        display: flex;
        margin-left: 5px;
        position: relative;
      }
      
      .pacman-dot {
        width: 10px;
        height: 10px;
        background-color: #FFFFFF;
        border-radius: 50%;
        margin-right: 15px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
        opacity: 1;
      }
      
      .pacman-dot:nth-child(1) {
        animation: dot-fade 0.7s infinite;
        animation-delay: 0s;
      }
      
      .pacman-dot:nth-child(2) {
        animation: dot-fade 0.7s infinite;
        animation-delay: 0.2s;
      }
      
      .pacman-dot:nth-child(3) {
        animation: dot-fade 0.7s infinite;
        animation-delay: 0.4s;
      }
      
      /* Click me label styles */
      .click-me-label {
        position: absolute;
        background-color: #333;
        color: white;
        padding: 5px 8px;
        border-radius: 10px;
        font-size: 12px;
        font-family: sans-serif;
        white-space: nowrap;
        right: 0;
        bottom: -25px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
        animation: pulse 1.5s infinite;
        pointer-events: none;
      }

      @keyframes pulse {
        0% { opacity: 0.7; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.05); }
        100% { opacity: 0.7; transform: scale(1); }
      }
      
      /* Interactive dot styles */
      .interactive-dot {
        position: absolute;
        width: 12px;
        height: 12px;
        background-color: #FFFFFF;
        border-radius: 50%;
        box-shadow: 0 0 5px rgba(255, 255, 255, 0.8);
        z-index: 998;
        transition: transform 0.2s, opacity 0.3s;
      }
      
      .interactive-dot.power-pellet {
        width: 20px;
        height: 20px;
        background-color: #00FFFF;
        animation: power-pellet-pulse 1s infinite alternate;
      }
      
      .interactive-dot.eaten {
        transform: scale(0);
        opacity: 0;
      }
      
      .score-display {
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: rgba(0, 0, 0, 0.7);
        color: white;
        padding: 5px 10px;
        border-radius: 10px;
        font-family: Arial, sans-serif;
        font-size: 16px;
        z-index: 999;
      }
      
      @keyframes power-pellet-pulse {
        0% { transform: scale(1); box-shadow: 0 0 5px rgba(0, 255, 255, 0.8); }
        100% { transform: scale(1.2); box-shadow: 0 0 15px rgba(0, 255, 255, 1); }
      }
      
      @keyframes dot-flicker {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
      }
      
      @keyframes dot-fade {
        0% { opacity: 1; transform: scale(1); }
        100% { opacity: 0; transform: scale(0); }
      }
      
      @keyframes chomp {
        0% { d: path('M50,50 L90,20 A40,40 0 0,1 90,80 Z'); }
        100% { d: path('M50,50 L90,45 A40,40 0 0,1 90,55 Z'); }
      }
    `;
    document.head.appendChild(styleEl);
  }

  setRandomTarget() {
    // Stick to the very edge of the screen as requested
    // Using adjusted margins to keep Pacman more visible
    const edgeMargin = 25; // Increased to keep character more visible
    const maxX = window.innerWidth - this.characterSize * 1.5; // Adjusted to prevent going off-screen
    const maxY = window.innerHeight - this.characterSize * 1.2;

    // Determine the next direction based on current position and direction
    // This creates a predictable pattern strictly around the outer edge
    if (this.currentDirection === 'right' && this.position.x >= maxX - 5) {
      // If we reach the right edge while going right, turn down
      this.currentDirection = 'down';
    } else if (this.currentDirection === 'down' && this.position.y >= maxY - 5) {
      // If we reach the bottom edge while going down, turn left
      this.currentDirection = 'left';
    } else if (this.currentDirection === 'left' && this.position.x <= edgeMargin + 5) {
      // If we reach the left edge while going left, turn up
      this.currentDirection = 'up';
    } else if (this.currentDirection === 'up' && this.position.y <= edgeMargin + 5) {
      // If we reach the top edge while going up, turn right
      this.currentDirection = 'right';
    }

    // Set target positions to the exact corners to ensure it follows the edge precisely
    switch (this.currentDirection) {
      case 'right':
        this.targetPosition = {
          x: maxX,
          y: edgeMargin
        };
        break;
      case 'down':
        this.targetPosition = {
          x: maxX,
          y: maxY
        };
        break;
      case 'left':
        this.targetPosition = {
          x: edgeMargin,
          y: maxY
        };
        break;
      case 'up':
        this.targetPosition = {
          x: edgeMargin,
          y: edgeMargin
        };
        break;
    }
  }

  animateRoaming() {
    if (!this.isRoaming || !this.roamingCharacter) {
      return;
    }

    // Check if we need to change direction based on our position
    this.setRandomTarget();

    // Determine movement angle (0, 90, 180, or 270 degrees for grid-like movement)
    let angle = 0;

    // Move in straight lines based on direction
    switch (this.currentDirection) {
      case 'right':
        this.position.x += this.speed;
        angle = 0;
        break;
      case 'down':
        this.position.y += this.speed;
        angle = 90;
        break;
      case 'left':
        this.position.x -= this.speed;
        angle = 180;
        break;
      case 'up':
        this.position.y -= this.speed;
        angle = 270;
        break;
    }

    // Keep Pac-Man within viewport boundaries
    const buffer = this.characterSize * 0.5; // Reduced buffer to keep more visible while still preventing overflow
    const maxX = window.innerWidth - this.characterSize * 1.5;
    const maxY = window.innerHeight - this.characterSize * 1.2;

    this.position.x = Math.max(buffer, Math.min(this.position.x, maxX));
    this.position.y = Math.max(buffer, Math.min(this.position.y, maxY));

    // Update the character's position and rotation
    this.updateCharacterPosition(angle);

    // Continue animation loop
    this.animationFrame = requestAnimationFrame(() => this.animateRoaming());
  }

  updateCharacterPosition(angle = 0) {
    if (!this.roamingCharacter) return;

    // Update the actual DOM position
    this.roamingCharacter.style.left = `${this.position.x}px`;
    this.roamingCharacter.style.top = `${this.position.y}px`;

    // Rotate the pacman to face movement direction
    const pacmanContainer = this.roamingCharacter.querySelector('.pacman-container');
    if (pacmanContainer) {
      pacmanContainer.style.transform = `rotate(${angle}deg)`;
    }
  }

  stopRoaming() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
    }

    if (this.targetTimeout) {
      clearTimeout(this.targetTimeout);
    }

    if (this.collisionInterval) {
      clearInterval(this.collisionInterval);
    }

    // Clear all interactive dots
    this.clearInteractiveDots();

    // Remove score display
    if (this.scoreDisplay && this.scoreDisplay.parentNode) {
      this.scoreDisplay.parentNode.removeChild(this.scoreDisplay);
      this.scoreDisplay = null;
    }

    this.isRoaming = false;

    // Remove the 3D character
    if (this.roamingCharacter) {
      this.roamingCharacter.remove();
      this.roamingCharacter = null;
    }

    // Reset score
    this.dotsEaten = 0;
  }
}

// Initialize the Old Wise One when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
  window.oldWiseOne = new OldWiseOne();
});

// If the document is already loaded, initialize immediately
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  setTimeout(() => {
    window.oldWiseOne = new OldWiseOne();
  }, 100);
}