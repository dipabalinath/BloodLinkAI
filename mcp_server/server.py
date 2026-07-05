"""
Main entry point for BloodLink MCP Server.
"""

from mcp.server.fastmcp import FastMCP
from mcp_server.config import HOST, PORT, SERVER_NAME, VERSION
from mcp_server.registry import registry
from utils.logger import logger

# Import all tool modules to trigger their @registry.register() decorators
import mcp_server.tools.inventory_tools as InventoryTools
import mcp_server.tools.donor_tools as DonorTools
import mcp_server.tools.request_tools as RequestTools
import mcp_server.tools.notification_tools as NotificationTools
import mcp_server.tools.analytics_tools as AnalyticsTools

logger.info(f"Initializing {SERVER_NAME} (v{VERSION}) MCP Server...")

# Initialize the FastMCP Server instance (mcp == 1.28.x)
mcp = FastMCP("BloodLink MCP")

# Automatically expose all registered tools
# Since we decorated all public methods/functions in the tool modules, 
# they are automatically collected in the registry.
registered_tools_count = 0
for tool_name in registry.list_tools():
    func = registry.get_tool(tool_name)
    mcp.tool()(func)
    logger.debug(f"Registered MCP Tool: {tool_name}")
    registered_tools_count += 1

logger.info(f"Successfully loaded {registered_tools_count} tools into FastMCP.")

def main():
    """Start the MCP server using stdio."""
    logger.info("Starting BloodLink MCP Server using STDIO transport...")
    try:
        # Run the server with stdio transport (compatible with FastMCP 1.28.1)
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")

if __name__ == "__main__":
    main()
