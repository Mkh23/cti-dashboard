"use client";

import { useEffect, useState } from "react";
import { listDevices, createDevice, listFarms, type Device, type Farm } from "@/lib/api";

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState({
    device_code: "",
    label: "",
    farm_id: "",
  });

  const loadData = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const [devicesData, farmsData] = await Promise.all([
        listDevices(token),
        listFarms(token),
      ]);
      setDevices(devicesData);
      setFarms(farmsData);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.device_code.trim()) return;
    
    setCreating(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      await createDevice(token, {
        device_code: formData.device_code,
        label: formData.label || undefined,
        farm_id: formData.farm_id || undefined,
      });
      setFormData({ device_code: "", label: "", farm_id: "" });
      setShowForm(false);
      await loadData();
    } catch (e: any) {
      setError(e.message || "Failed to create device");
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <main className="p-6"><p>Loading devices...</p></main>;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Device Registry</h1>
          <p className="mt-2 text-gray-400">
            Manage devices and their configurations
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          {showForm ? "Cancel" : "Register Device"}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-red-900/20 border border-red-500 p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Create Device Form */}
      {showForm && (
        <div className="mt-8 card">
          <h2 className="text-xl font-semibold mb-4">Register New Device</h2>
          <form onSubmit={handleCreateDevice} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Device Code *
              </label>
              <input
                type="text"
                placeholder="e.g., dev-0001"
                value={formData.device_code}
                onChange={(e) => setFormData({ ...formData, device_code: e.target.value })}
                className="w-full rounded-md bg-gray-800 border border-gray-700 px-4 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={creating}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Label
              </label>
              <input
                type="text"
                placeholder="e.g., North Barn Pi"
                value={formData.label}
                onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                className="w-full rounded-md bg-gray-800 border border-gray-700 px-4 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={creating}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Farm
              </label>
              <select
                value={formData.farm_id}
                onChange={(e) => setFormData({ ...formData, farm_id: e.target.value })}
                className="w-full rounded-md bg-gray-800 border border-gray-700 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={creating}
              >
                <option value="">No farm assigned</option>
                {farms.map((farm) => (
                  <option key={farm.id} value={farm.id}>
                    {farm.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-4">
              <button
                type="submit"
                disabled={creating || !formData.device_code.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creating ? "Registering..." : "Register Device"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-6 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600"
                disabled={creating}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Devices List */}
      <div className="mt-8">
        <h2 className="text-2xl font-semibold mb-4">
          Devices ({devices.length})
        </h2>
        
        {devices.length === 0 ? (
          <div className="card text-center py-12">
            <p className="text-gray-400">No devices registered yet. Click "Register Device" to add one.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {devices.map((device) => {
              const farm = farms.find((f) => f.id === device.farm_id);
              return (
                <div key={device.id} className="card">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-semibold">{device.device_code}</h3>
                        {device.label && (
                          <span className="text-sm text-gray-400">({device.label})</span>
                        )}
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-gray-400">Farm</p>
                          <p className="text-white">{farm?.name || "Not assigned"}</p>
                        </div>
                        <div>
                          <p className="text-gray-400">Captures</p>
                          <p className="text-white">{device.captures_count}</p>
                        </div>
                        <div>
                          <p className="text-gray-400">Last Upload</p>
                          <p className="text-white">
                            {device.last_upload_at
                              ? new Date(device.last_upload_at).toLocaleString()
                              : "Never"}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-400">S3 Prefix</p>
                          <p className="text-white text-xs font-mono">
                            {device.s3_prefix_hint || "N/A"}
                          </p>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-3">
                        ID: {device.id}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600">
                        Edit
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
