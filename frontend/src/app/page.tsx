"use client"

import React from "react";
import ScientificChatbot from "@/components/scientific/scientific-chatbot";
import MainLayout from "@/components/layout/main-layout";

export default function Home() {
  return (
    <MainLayout 
      chatComponent={<ScientificChatbot />}
    />
  );
}
