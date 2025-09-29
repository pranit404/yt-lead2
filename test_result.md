#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "Upgrade existing YouTube lead generation system to have centralized database with 2 collections (leads with email, leads without email), Discord bot integration for starting programs with parameters, and real-time notifications for each email found/not found and program start/finish. Change outreach from collaboration to client acquisition for video editing services."

backend:
  - task: "Enhanced FastAPI Backend Integration"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Integrated comprehensive YouTube lead generation backend with MongoDB, email extraction using Playwright, AI-powered client outreach using Gemini, real-time Discord notifications, and full API endpoints for lead management"

  - task: "MongoDB Database Setup"  
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "MongoDB collections configured: main_leads (with emails), no_email_leads (without emails), processing_status for tracking. Uses environment variables for connection."

  - task: "Discord Bot with MongoDB Integration"
    implemented: true
    working: true
    file: "/app/discord_bot.py"  
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Created comprehensive Discord bot with commands: !start (with all parameters), !status, !leads, !export, !clear. Integrated with MongoDB and backend API for full functionality."

  - task: "Client Outreach Email Generation"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"  
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Replaced collaboration emails with client acquisition outreach for video editing services. Uses Gemini AI for personalized emails offering professional video editing services to creators."

  - task: "Email Extraction Bug Fix"
    implemented: true
    working: false
    file: "/app/backend/server.py"
    stuck_count: 1
    priority: "critical"
    needs_retesting: false
    status_history:
        -working: false
        -agent: "user"
        -comment: "User reported ALL emails in YouTube about pages were being missed by the software"
        -working: false
        -agent: "main"
        -comment: "Fixed email extraction with improved web scraping (better element targeting, 'Show more' button handling, longer wait times) and enhanced email regex patterns (handles obfuscation, multiple patterns, better validation). Added debug endpoints for testing."
        -working: false
        -agent: "testing"
        -comment: "CRITICAL ISSUES FOUND: 1) Obfuscated [at] [dot] pattern fails - spaces remain after replacement (business @ creator . com), 2) Underscore in domain names not supported in regex patterns [a-zA-Z0-9.-], 3) Web scraping completely broken - Playwright browser installation issues prevent any channel scraping. Text extraction API works for basic emails but fails on 2 critical patterns. Debug endpoints functional."

frontend:
  - task: "Enhanced Frontend Dashboard"
    implemented: true  
    working: true
    file: "/app/frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Updated React dashboard with client-focused UI, improved lead cards showing email status, outreach status, enhanced filtering options, and better visual design for client lead management"

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "Backend API Testing"
    - "Discord Bot Testing"  
    - "Frontend Integration Testing"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: "Successfully upgraded YouTube lead generation system with all requested features: centralized MongoDB database (2 collections), Discord bot with comprehensive commands and real-time notifications, client outreach emails instead of collaboration, enhanced frontend dashboard. System ready for configuration and testing."
    -agent: "main"
    -message: "CRITICAL BUG FIX: User reported ALL emails in YouTube about pages were being missed. Improved email extraction with: 1) Enhanced web scraping with better element targeting and 'Show more' button handling, 2) Improved email regex patterns with obfuscation handling, 3) Added debug endpoints for testing. Changes applied to scrape_channel_about_page() and extract_email_from_text() functions."