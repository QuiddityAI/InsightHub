<script setup>
import {
  AdjustmentsHorizontalIcon,
  MinusCircleIcon,
  HomeIcon,
  ArrowRightOnRectangleIcon,
  UserCircleIcon,
  CircleStackIcon,
  ClockIcon,
  BookmarkIcon
} from "@heroicons/vue/24/outline";
import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
const _window = window
const _history = history
</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
      show_change_password: false,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
  },
  methods: {
    change_password(old_password, new_password, new_password_repeat) {
      if (!old_password || !new_password || !new_password_repeat) {
        this.$toast.add({severity:'error', summary:'Error', detail:'Please fill out all fields'})
        return
      }
      if (new_password !== new_password_repeat) {
        this.$toast.add({severity:'error', summary:'Error', detail:'New passwords do not match'})
        return
      }
      djangoClient.post(`/org/change_password_from_app/`, {
        old_password: old_password,
        new_password: new_password,
      }).then(() => {
        this.$toast.add({severity: 'success', summary: 'Success', detail: 'Password changed', life: 5000})
        alert("Password changed. Please log in again.")
        window.location.assign('/')
      }).catch((error) => {
        this.$toast.add({severity: 'error', summary: 'Error', detail: 'Password change failed', life: 5000})
      })
      this.$refs.old_password.value = ""
      this.$refs.new_password.value = ""
      this.$refs.new_password_repeat.value = ""
    },
  },
}
</script>

<template>
  <div class="flex flex-col gap-1">
      <button
        v-if="appState.logged_in"
        @click="djangoClient.post(`/org/logout/`).then(() => { _window.location.assign('/') })"
        title="Logout"
        class="rounded p-2 text-sm text-gray-500 bg-gray-100 hover:bg-blue-100/50">
        Logout <ArrowRightOnRectangleIcon class="w-4 inline"></ArrowRightOnRectangleIcon>
      </button>
    <hr>
    <button @click="show_change_password = !show_change_password"
      class="text-sm text-gray-500 rounded-md p-2 bg-gray-100 hover:bg-blue-100/50">
      Change Password
    </button>
    <div v-if="show_change_password" class="flex flex-col gap-1">
      <input ref="old_password" type="password" placeholder="Old Password" class="w-full rounded-md border-0 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
      <input ref="new_password" type="password" placeholder="New Password" class="w-full rounded-md border-0 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
      <input ref="new_password_repeat" type="password" placeholder="Repeat New Password" @keyup.enter="change_password($refs.old_password.value, $refs.new_password.value, $refs.new_password_repeat.value)"
        class="w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
      <button @click="change_password($refs.old_password.value, $refs.new_password.value, $refs.new_password_repeat.value)"
        class="w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6 bg-gray-100 hover:bg-blue-100/50">
        Change Password
      </button>
    </div>
    <div class="flex flex-row items-center gap-1"
      v-if="appState.logged_in && appState.user?.is_staff">
      <a
        :href="`org/admin/`"
        title="Manage Datasets"
        class="w-8 rounded p-2 text-sm text-gray-500 hover:bg-gray-100">
        <CircleStackIcon></CircleStackIcon>
      </a>
      <button
        @click="appState.toggle_dev_mode()"
        class="rounded px-1 py-2 text-xs text-gray-500 hover:bg-gray-100"
        :class="{'ring-1 ring-green-200': appState.dev_mode}">
        Dev
      </button>
    </div>
  </div>
</template>

<style scoped>
</style>
