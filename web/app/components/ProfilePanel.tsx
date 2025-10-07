"use client";
import { useState } from "react";
import { Profile, updateProfile, changePassword, UpdateProfileData, ChangePasswordData } from "@/lib/api";

interface ProfilePanelProps {
  profile: Profile;
  onProfileUpdate?: (profile: Profile) => void;
}

export default function ProfilePanel({ profile, onProfileUpdate }: ProfilePanelProps) {
  const [activeTab, setActiveTab] = useState<"profile" | "password">("profile");
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Profile form state
  const [fullName, setFullName] = useState(profile.full_name || "");
  const [phoneNumber, setPhoneNumber] = useState(profile.phone_number || "");
  const [address, setAddress] = useState(profile.address || "");

  // Password form state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");

      const data: UpdateProfileData = {
        full_name: fullName || null,
        phone_number: phoneNumber || null,
        address: address || null,
      };

      const updatedProfile = await updateProfile(token, data);
      setMessage({ type: "success", text: "Profile updated successfully!" });
      setIsEditing(false);
      if (onProfileUpdate) {
        onProfileUpdate(updatedProfile);
      }
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to update profile" });
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    // Validate passwords match
    if (newPassword !== confirmPassword) {
      setMessage({ type: "error", text: "New passwords do not match" });
      setSaving(false);
      return;
    }

    // Validate password strength (basic)
    if (newPassword.length < 8) {
      setMessage({ type: "error", text: "Password must be at least 8 characters" });
      setSaving(false);
      return;
    }

    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");

      const data: ChangePasswordData = {
        current_password: currentPassword,
        new_password: newPassword,
      };

      await changePassword(token, data);
      setMessage({ type: "success", text: "Password changed successfully!" });
      
      // Clear password fields
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to change password" });
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setFullName(profile.full_name || "");
    setPhoneNumber(profile.phone_number || "");
    setAddress(profile.address || "");
    setIsEditing(false);
    setMessage(null);
  };

  return (
    <div className="card">
      <h2 className="text-2xl font-bold mb-6">Profile Management</h2>

      {/* Tab Navigation */}
      <div className="flex space-x-4 border-b border-gray-700 mb-6">
        <button
          className={`pb-2 px-4 ${
            activeTab === "profile"
              ? "border-b-2 border-blue-500 text-blue-500"
              : "text-gray-400 hover:text-gray-300"
          }`}
          onClick={() => {
            setActiveTab("profile");
            setMessage(null);
          }}
        >
          Profile Information
        </button>
        <button
          className={`pb-2 px-4 ${
            activeTab === "password"
              ? "border-b-2 border-blue-500 text-blue-500"
              : "text-gray-400 hover:text-gray-300"
          }`}
          onClick={() => {
            setActiveTab("password");
            setMessage(null);
          }}
        >
          Change Password
        </button>
      </div>

      {/* Messages */}
      {message && (
        <div
          className={`mb-4 p-3 rounded ${
            message.type === "success"
              ? "bg-green-900 text-green-100 border border-green-700"
              : "bg-red-900 text-red-100 border border-red-700"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Profile Information Tab */}
      {activeTab === "profile" && (
        <form onSubmit={handleSaveProfile}>
          <div className="space-y-4">
            {/* Email (read-only) */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Email
              </label>
              <input
                type="email"
                value={profile.email}
                disabled
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-500 cursor-not-allowed"
              />
              <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
            </div>

            {/* Full Name */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={!isEditing || isSaving}
                className={`w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white ${
                  isEditing ? "" : "cursor-not-allowed text-gray-400"
                }`}
                placeholder="Enter your full name"
              />
            </div>

            {/* Phone Number */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Phone Number
              </label>
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                disabled={!isEditing || isSaving}
                className={`w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white ${
                  isEditing ? "" : "cursor-not-allowed text-gray-400"
                }`}
                placeholder="+1-555-1234"
              />
            </div>

            {/* Address */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Address
              </label>
              <textarea
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                disabled={!isEditing || isSaving}
                rows={3}
                className={`w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white ${
                  isEditing ? "" : "cursor-not-allowed text-gray-400"
                }`}
                placeholder="123 Main St, City, State ZIP"
              />
            </div>

            {/* Roles (read-only) */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Roles
              </label>
              <div className="flex gap-2">
                {profile.roles.map((role) => (
                  <span
                    key={role}
                    className="px-3 py-1 bg-blue-900 text-blue-100 rounded-full text-sm"
                  >
                    {role}
                  </span>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              {!isEditing ? (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="btn"
                >
                  Edit Profile
                </button>
              ) : (
                <>
                  <button
                    type="submit"
                    disabled={isSaving}
                    className="btn"
                  >
                    {isSaving ? "Saving..." : "Save Changes"}
                  </button>
                  <button
                    type="button"
                    onClick={handleCancelEdit}
                    disabled={isSaving}
                    className="px-4 py-2 bg-gray-700 text-gray-200 rounded hover:bg-gray-600"
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </div>
        </form>
      )}

      {/* Change Password Tab */}
      {activeTab === "password" && (
        <form onSubmit={handleChangePassword}>
          <div className="space-y-4">
            {/* Current Password */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Current Password
              </label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                disabled={isSaving}
                required
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white"
                placeholder="Enter current password"
              />
            </div>

            {/* New Password */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                New Password
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={isSaving}
                required
                minLength={8}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white"
                placeholder="Enter new password (min 8 characters)"
              />
            </div>

            {/* Confirm New Password */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Confirm New Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isSaving}
                required
                minLength={8}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white"
                placeholder="Confirm new password"
              />
            </div>

            {/* Action Button */}
            <div className="pt-4">
              <button
                type="submit"
                disabled={isSaving}
                className="btn"
              >
                {isSaving ? "Changing..." : "Change Password"}
              </button>
            </div>
          </div>
        </form>
      )}
    </div>
  );
}
