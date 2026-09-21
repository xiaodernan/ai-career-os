import { redirect } from "next/navigation";

export default function Home() {
  // The (app) layout's client guard routes unauthenticated users to /login.
  redirect("/dashboard");
}
