import streamlit as st
import json
from utils.logger import logger

def sanitize_error_message(error_str):
    """Return a readable error message without stack traces."""
    err_str = str(error_str).lower()
    if "inventory" in err_str:
        return "The inventory search could not be completed because the inventory service is temporarily unavailable."
    if "priority" in err_str:
        return "Clinical priority assessment could not be completed at this time."
    if "eligibility" in err_str:
        return "Donor eligibility criteria could not be verified."
    if "notification" in err_str:
        return "Emergency notifications could not be dispatched."
    if "recommendation" in err_str:
        return "AI recommendations are temporarily unavailable."
    
    return "An internal agent service is temporarily unavailable. Please try again later."

def generate_fallback_summary(agent_data):
    """Generate a readable summary if final_answer is missing or empty."""
    summary = "### 🩸 BloodLink AI Response Summary\n\n"
    
    if "priority" in agent_data:
        p_data = agent_data["priority"]
        priority = p_data.get("priority", "Unknown")
        reason = p_data.get("reason", "No reason provided.")
        summary += f"**Priority Assessment:** {priority}\n> {reason}\n\n"
        
    if "inventory" in agent_data:
        i_data = agent_data["inventory"]
        inv_sum = i_data.get("summary", "Inventory checked.")
        summary += f"**Inventory Status:**\n> {inv_sum}\n\n"
        
    if "recommendation" in agent_data:
        r_data = agent_data["recommendation"]
        rec = r_data.get("top_recommendation")
        if rec:
            summary += f"**Top Recommendation:**\n> {rec.get('facility')} ({rec.get('blood_group')}: {rec.get('units')} units)\n\n"
            
    if "notification" in agent_data:
        n_data = agent_data["notification"]
        status = n_data.get("status", "Unknown")
        summary += f"**Notifications:**\n> Dispatch status: {status}\n\n"
        
    return summary

def render_agent_execution_panel(agents_involved, agent_data):
    """Render a visual summary of agent execution status."""
    st.markdown("### 🤖 Agent Execution Summary")
    
    if not agents_involved:
        st.write("No specialized agents were invoked for this request.")
        return
        
    # Create a clean grid of cards
    cols = st.columns(min(len(agents_involved), 4) or 1)
    
    for idx, agent in enumerate(agents_involved):
        data = agent_data.get(agent, {})
        status = data.get("status", "Completed") if data else "Completed"
        
        # Determine icon and styling
        if status.lower() in ["success", "completed"]:
            icon = "✅"
            style_type = "success"
        elif status.lower() in ["error", "failed"]:
            icon = "❌"
            style_type = "error"
        else:
            icon = "⚠️"
            style_type = "warning"
            
        with cols[idx % len(cols)]:
            if style_type == "success":
                st.success(f"{icon} **{agent.title()}**\n\nStatus: {status}")
            elif style_type == "error":
                st.error(f"{icon} **{agent.title()}**\n\nStatus: {status}")
            else:
                st.warning(f"{icon} **{agent.title()}**\n\nStatus: {status}")

def render_workflow_panel(agent_data):
    """Render the expandable technical JSON details for transparency."""
    with st.expander("🔍 View Agent Workflow & Reasoning"):
        if not agent_data:
            st.write("No workflow data available.")
            return
            
        for agent, data in agent_data.items():
            st.markdown(f"#### {agent.title()} Agent Output")
            st.json(data)

def render_assistant_message(message):
    """Render a single assistant message from history, including cards and expanders."""
    # 1. Main natural language response
    st.markdown(message["content"])
    
    # 2. Detailed workflow components
    if message.get("details"):
        details = message["details"]
        agents_involved = details.get("agents_involved", [])
        agent_data = details.get("agent_data", {})
        
        st.markdown("---")
        render_agent_execution_panel(agents_involved, agent_data)
        render_workflow_panel(agent_data)

def render_assistant():
    """Render the AI Assistant chat interface."""
    st.header("🧠 BloodLink AI Copilot")
    st.write("Interact with the specialized healthcare AI agents.")

    orchestrator = st.session_state.get('orchestrator')
    if not orchestrator:
        st.error("Orchestrator not initialized. Check system logs.")
        return

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Hello! I am the BloodLink AI Copilot. I can help coordinate inventory searches, donor eligibility, priority triage, and emergency dispatch. How can I assist you today?"}
        ]

    # Display chat messages from history on app rerun
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "details" in message:
                render_assistant_message(message)
            else:
                st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("e.g., We have a massive hemorrhage patient needing O- blood at General Hospital."):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            with st.spinner("BloodLink AI agents are analyzing and coordinating a response..."):
                try:
                    response = orchestrator.process_request(prompt)
                    
                    agents_involved = response.get('agents_involved', [])
                    agent_data = response.get('agent_data', {})
                    
                    if response.get("status") == "Success":
                        final_answer = response.get("final_answer")
                        if not final_answer or not final_answer.strip():
                            final_answer = generate_fallback_summary(agent_data)
                            
                        new_msg = {
                            "role": "assistant", 
                            "content": final_answer,
                            "details": {
                                "agents_involved": agents_involved,
                                "agent_data": agent_data
                            }
                        }
                        
                        # Render it visually right now
                        render_assistant_message(new_msg)
                        
                        # Save to history
                        st.session_state.chat_messages.append(new_msg)
                    else:
                        raw_error = response.get('error', 'Unknown error.')
                        readable_error = sanitize_error_message(raw_error)
                        
                        error_msg = f"**I encountered an issue processing your request:**\n\n{readable_error}"
                        
                        new_msg = {
                            "role": "assistant", 
                            "content": error_msg,
                            "details": {
                                "agents_involved": agents_involved,
                                "agent_data": agent_data
                            }
                        }
                        
                        render_assistant_message(new_msg)
                        st.session_state.chat_messages.append(new_msg)
                        
                except Exception as e:
                    readable_error = sanitize_error_message(e)
                    st.error(f"Failed to communicate with AI orchestration layer: {readable_error}")
                    logger.error(f"AI Assistant Error: {e}", exc_info=True)
