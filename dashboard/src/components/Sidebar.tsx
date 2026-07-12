import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  GitBranch,
  Server,
  ShoppingCart,
  Settings,
  ChevronLeft,
  ChevronRight,
  Hexagon,
  Radio,
} from 'lucide-react'
import { useState } from 'react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/pipelines', icon: GitBranch, label: 'Pipelines' },
]

const navSubItems = [
  { to: '/pipelines/live', icon: Radio, label: 'Live View', parent: '/pipelines' },
]

const bottomNavItems = [
  { to: '/nodes', icon: Server, label: 'Nodes' },
  { to: '/marketplace', icon: ShoppingCart, label: 'Marketplace' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={`h-screen fixed left-0 top-0 z-30 flex flex-col border-r border-surface-800 bg-surface-950 transition-all duration-200 ${
        collapsed ? 'w-16' : 'w-60'
      }`}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 h-14 px-4 border-b border-surface-800">
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-primary-600/20 flex items-center justify-center">
          <Hexagon className="w-5 h-5 text-primary-400" />
        </div>
        {!collapsed && (
          <span className="text-sm font-bold text-white tracking-tight">
            Supra<span className="text-primary-400">Codex</span>
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 space-y-1 px-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150
              ${
                isActive
                  ? 'bg-primary-600/10 text-primary-400 border border-primary-600/20'
                  : 'text-surface-400 hover:text-surface-200 hover:bg-surface-800/50 border border-transparent'
              }`
            }
          >
            <item.icon className="w-4 h-4 flex-shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
        {/* Sub-items */}
        {navSubItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ml-6
              ${
                isActive
                  ? 'text-primary-400'
                  : 'text-surface-500 hover:text-surface-300'
              }`
            }
          >
            <item.icon className="w-3.5 h-3.5 flex-shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
        <div className="my-2 border-t border-surface-800 mx-2" />
        {bottomNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150
              ${
                isActive
                  ? 'bg-primary-600/10 text-primary-400 border border-primary-600/20'
                  : 'text-surface-400 hover:text-surface-200 hover:bg-surface-800/50 border border-transparent'
              }`
            }
          >
            <item.icon className="w-4 h-4 flex-shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="p-2 border-t border-surface-800">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center w-full p-2 rounded-lg text-surface-500 hover:text-surface-300 hover:bg-surface-800 transition-colors"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  )
}