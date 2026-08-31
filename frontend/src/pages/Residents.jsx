import { useMemo, useState } from "react";
import {
  Loader2,
  AlertCircle,
  Inbox,
  Users,
  UserCheck,
  UserX,
  Search,
  Plus,
  MoreHorizontal,
  Pencil,
  Trash2,
  Link2,
} from "lucide-react";

// NOTE: adjust these import paths if useResidents / useProperties live
// somewhere else in your project (e.g. a shared hooks barrel) — only the
// hook names and React Query contract (data / isLoading / isError / error)
// are assumed here, not the file location. Nothing about these hooks is
// modified.
import {
  useResidents,
  useCreateResident,
  useUpdateResident,
  useDeleteResident,
  useAssignResidentProperty,
} from "@/hooks/useResidents";
import { useProperties } from "@/hooks/useProperties";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

/* ------------------------------------------------------------------ */
/* Helpers                                                              */
/*                                                                      */
/* Confirmed /api/residents/ response shape:                           */
/*   { resident_id, name, phone, email, gender, status, registered_at } */
/* Field access below is direct — no shape-detection needed anymore.    */
/* ------------------------------------------------------------------ */

function detectField(row, pattern, exclude) {
  if (!row) return undefined;
  return Object.keys(row).find(
    (key) => pattern.test(key) && !(exclude && exclude.test(key))
  );
}

function formatCellValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function getInitials(value) {
  if (typeof value !== "string" || !value.trim()) return "?";
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function statusBadgeVariant(value) {
  const normalized = String(value ?? "").toLowerCase();
  if (/^active$/.test(normalized)) return "success";
  if (/^inactive$/.test(normalized)) return "destructive";
  if (/pending|review/.test(normalized)) return "warning";
  return "secondary";
}

/* ------------------------------------------------------------------ */
/* Section states                                                      */
/* ------------------------------------------------------------------ */

function SectionLoading() {
  return (
    <div className="flex items-center justify-center gap-2 py-14 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      Loading residents...
    </div>
  );
}

function SectionError({ error }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
      <AlertCircle className="h-4 w-4 shrink-0" />
      {error?.message || "Something went wrong while loading residents."}
    </div>
  );
}

function SectionEmpty({ label = "No residents found." }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-14 text-center text-muted-foreground">
      <Inbox className="h-6 w-6" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Create / Edit form dialog (shared) — styled to match Properties'    */
/* PropertyForm dialog layout.                                         */
/* ------------------------------------------------------------------ */

function ResidentFormDialog({
  open,
  onOpenChange,
  title,
  description,
  initialValues,
  fields,
  onSubmit,
  submitLabel,
}) {
  const [values, setValues] = useState(initialValues);

  function handleChange(key, value) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    onSubmit(values);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            {fields.map((field) => (
              <div
                key={field.key}
                className={`flex flex-col gap-1.5 ${field.fullWidth ? "sm:col-span-2" : ""}`}
              >
                <Label htmlFor={field.key}>{field.label}</Label>
                <Input
                  id={field.key}
                  type={field.type || "text"}
                  value={values[field.key] ?? ""}
                  onChange={(event) => handleChange(field.key, event.target.value)}
                  required={field.required}
                  placeholder={field.placeholder}
                />
              </div>
            ))}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">{submitLabel}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Delete confirmation dialog                                          */
/* ------------------------------------------------------------------ */

function DeleteResidentDialog({ resident, onOpenChange, onConfirm, displayName }) {
  return (
    <Dialog open={!!resident} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete resident</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Are you sure you want to delete{" "}
          <span className="font-medium text-foreground">{displayName}</span>? This action
          cannot be undone.
        </p>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" variant="destructive" onClick={() => onConfirm(resident)}>
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Assign property dialog                                              */
/*                                                                      */
/* This remains a separate operation backed by the Properties API,     */
/* which is unaffected by the Residents data-contract correction.      */
/*                                                                      */
/* IMPORTANT: this dialog intentionally uses a native <select> instead  */
/* of the shared Base UI <Select> component. Base UI Select inside a    */
/* Dialog previously caused dropdown flicker in this project — this is  */
/* a deliberate workaround, not an oversight, and shared select.tsx is  */
/* left untouched.                                                      */
/* ------------------------------------------------------------------ */

function AssignPropertyDialog({
  resident,
  properties,
  propertiesQuery,
  onOpenChange,
  onConfirm,
  displayName,
  errorMessage,
}) {
  const [selectedId, setSelectedId] = useState("");

  const propertyIdField = "property_id";
  const propertyNumberField = "property_number";

  return (
    <Dialog open={!!resident} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign property</DialogTitle>
          <DialogDescription>
            Choose a property to assign to{" "}
            <span className="font-medium text-foreground">{displayName}</span>.
          </DialogDescription>
        </DialogHeader>

        <div className="py-2">
          {propertiesQuery.isLoading ? (
            <SectionLoading />
          ) : propertiesQuery.isError ? (
            <SectionError error={propertiesQuery.error} />
          ) : !properties || properties.length === 0 ? (
            <SectionEmpty label="No properties available to assign." />
          ) : (
            <div className="grid gap-1.5">
              <Label htmlFor="assign-property-select">Property</Label>
              <select
                id="assign-property-select"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="" disabled>
                  Select a property
                </option>
                {properties.map((property) => (
                  <option
                    key={property[propertyIdField]}
                    value={String(property[propertyIdField])}
                  >
                    {formatCellValue(property[propertyNumberField])}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        {errorMessage && (
          <div
            role="alert"
            className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
          >
            {errorMessage}
          </div>
          )}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" disabled={!selectedId} onClick={() => onConfirm(resident, selectedId)}>
            Assign property
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Shared stat card — matches Properties' StatCard exactly             */
/* ------------------------------------------------------------------ */

function StatCard({ icon, label, value, loading }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <span className="text-muted-foreground">{icon}</span>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold">
          {loading ? <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /> : value}
        </div>
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Main page                                                            */
/* ------------------------------------------------------------------ */

export default function Residents() {
  const createResidentMutation = useCreateResident();
  const updateResidentMutation = useUpdateResident();
  const deleteResidentMutation = useDeleteResident();
  const assignResidentPropertyMutation = useAssignResidentProperty();

  const residentsQuery = useResidents();
  const propertiesQuery = useProperties();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const [createOpen, setCreateOpen] = useState(false);
  const [editResident, setEditResident] = useState(null);
  const [deleteResident, setDeleteResident] = useState(null);
  const [assignResident, setAssignResident] = useState(null);
  const [assignError, setAssignError] = useState("");

  const residents = Array.isArray(residentsQuery.data) ? residentsQuery.data : [];

  const statusOptions = useMemo(() => {
    return Array.from(new Set(residents.map((row) => row.status).filter(Boolean)));
  }, [residents]);

  const filteredResidents = useMemo(() => {
    return residents.filter((row) => {
      const matchesStatus = statusFilter === "all" || row.status === statusFilter;
      if (!matchesStatus) return false;
      if (!search.trim()) return true;
      const term = search.trim().toLowerCase();
      const searchable = [row.name, row.email, row.phone, row.gender, row.status];
      return searchable.some(
        (value) => typeof value === "string" && value.toLowerCase().includes(term)
      );
    });
  }, [residents, search, statusFilter]);

  const hasActiveFilters = search.trim() !== "" || statusFilter !== "all";

  const clearFilters = () => {
    setSearch("");
    setStatusFilter("all");
  };

  const totalResidents = residents.length;
  const activeCount = residents.filter((row) => /^active$/i.test(String(row.status ?? ""))).length;
  const inactiveCount = residents.filter((row) => /^inactive$/i.test(String(row.status ?? ""))).length;

  const genderBreakdown = useMemo(() => {
    const male = residents.filter((row) => /^male$/i.test(String(row.gender ?? ""))).length;
    const female = residents.filter((row) => /^female$/i.test(String(row.gender ?? ""))).length;
    return { male, female };
  }, [residents]);

  /* ---------------------------------------------------------------- */
  /* Stub mutation handlers.                                           */
  /* useCreateResident / useUpdateResident / useDeleteResident /       */
  /* useAssignResidentProperty do not exist yet. Per instructions,     */
  /* these remain stubbed rather than invented — swap each body for a  */
  /* real mutation call (e.g. `const { mutate } = useCreateResident()`)*/
  /* once those hooks are added.                                       */
  /* ---------------------------------------------------------------- */

  async function handleCreateResident(formValues) {
    try {
      await createResidentMutation.mutateAsync(formValues);
      setCreateOpen(false);
    } catch (error) {
      console.error(
        "Failed to create resident:",
        error?.response?.data || error
      );
    }
  }

  async function handleUpdateResident(formValues) {
    if (!editResident) return;

    try {
      await updateResidentMutation.mutateAsync({
        residentId: editResident.resident_id,
        data: {
          name: formValues.name,
          email: formValues.email,
          phone: formValues.phone,
          gender: formValues.gender,
          status: formValues.status,
        },
      });

      setEditResident(null);
    } catch (error) {
      console.error(
        "Failed to update resident:",
        error?.response?.data || error
      );
    }
  }

  async function handleConfirmDelete(resident) {
    if (!resident) return;

    try {
      await deleteResidentMutation.mutateAsync(
        resident.resident_id
      );

      setDeleteResident(null);
    } catch (error) {
      console.error(
        "Failed to delete resident:",
        error?.response?.data || error
      );
    }
  }

  async function handleConfirmAssign(resident, propertyId) {
    if (!resident || !propertyId) return;

    setAssignError("");

    try {
      const result = await assignResidentPropertyMutation.mutateAsync({
        resident_id: resident.resident_id,
        property_id: propertyId,
      });

      console.log("ASSIGN SUCCESS:", result);
      setAssignResident(null);
    } catch (error) {
      const message =
        error?.response?.data?.error ||
        error?.message ||
        "Failed to assign property.";

      setAssignError(message);
    }
  }

  const formFields = [
    {
      key: "name",
      label: "Full name",
      required: true,
      placeholder: "Jane Doe",
      fullWidth: true,
    },
    {
      key: "email",
      label: "Email",
      type: "email",
      required: true,
      placeholder: "jane@example.com",
    },
    {
      key: "phone",
      label: "Phone",
      required: true,
      placeholder: "08012345678",
    },
    {
      key: "gender",
      label: "Gender",
      required: true,
      placeholder: "Male or Female",
    },
    {
      key: "status",
      label: "Status",
      required: true,
      placeholder: "Active or Inactive",
    },
  ];

  const displayName = (resident) => (resident ? formatCellValue(resident.name) : "");

  return (
    <div className="flex flex-col gap-6 p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Residents</h1>
          <p className="text-sm text-muted-foreground">
            Manage resident records and their statuses across the estate.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="gap-2 w-full sm:w-auto">
          <Plus className="h-4 w-4" />
          Add resident
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={<Users className="h-4 w-4" />}
          label="Total residents"
          value={formatCellValue(totalResidents)}
          loading={residentsQuery.isLoading}
        />
        <StatCard
          icon={<UserCheck className="h-4 w-4" />}
          label="Active"
          value={formatCellValue(activeCount)}
          loading={residentsQuery.isLoading}
        />
        <StatCard
          icon={<UserX className="h-4 w-4" />}
          label="Inactive"
          value={formatCellValue(inactiveCount)}
          loading={residentsQuery.isLoading}
        />
        <StatCard
          icon={<Users className="h-4 w-4" />}
          label="Male / Female"
          value={`${genderBreakdown.male} / ${genderBreakdown.female}`}
          loading={residentsQuery.isLoading}
        />
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, email, phone, gender, or status..."
              className="pl-9"
            />
          </div>

          {statusOptions.length > 0 && (
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-44">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                {statusOptions.map((status) => (
                  <SelectItem key={status} value={status}>
                    {status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {hasActiveFilters && (
            <Button variant="ghost" onClick={clearFilters}>
              Clear filters
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {residentsQuery.isLoading ? (
            <SectionLoading />
          ) : residentsQuery.isError ? (
            <SectionError error={residentsQuery.error} />
          ) : filteredResidents.length === 0 ? (
            <SectionEmpty
              label={
                hasActiveFilters
                  ? "No residents match your search or filters."
                  : "No residents found."
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Resident</TableHead>
                  <TableHead className="hidden md:table-cell">Email</TableHead>
                  <TableHead className="hidden sm:table-cell">Phone</TableHead>
                  <TableHead className="hidden lg:table-cell">Gender</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-10">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredResidents.map((row, index) => (
                  <TableRow key={row.resident_id ?? index}>
                    <TableCell className="whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Avatar className="h-7 w-7">
                          <AvatarFallback className="text-xs">
                            {getInitials(typeof row.name === "string" ? row.name : "")}
                          </AvatarFallback>
                        </Avatar>
                        <span className="font-medium text-foreground">
                          {formatCellValue(row.name)}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      {formatCellValue(row.email)}
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">
                      {formatCellValue(row.phone)}
                    </TableCell>
                    <TableCell className="hidden lg:table-cell">
                      {formatCellValue(row.gender)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariant(row.status)}>
                        {formatCellValue(row.status)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => setEditResident(row)}>
                            <Pencil className="mr-2 h-3.5 w-3.5" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setAssignResident(row)}>
                            <Link2 className="mr-2 h-3.5 w-3.5" />
                            Assign property
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => setDeleteResident(row)}
                            className="text-destructive focus:text-destructive"
                          >
                            <Trash2 className="mr-2 h-3.5 w-3.5" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create resident dialog */}
      <ResidentFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="Add resident"
        description="Enter the resident's details below."
        initialValues={{
          name: "",
          email: "",
          phone: "",
          gender: "",
        }}

        fields={formFields}
        onSubmit={handleCreateResident}
        submitLabel="Create resident"
      />

      {/* Edit resident dialog — remounts fresh per resident via `key`, so
          no useEffect is needed to sync initial form values. */}
      {editResident && (
        <ResidentFormDialog
          key={editResident.resident_id ?? displayName(editResident)}
          open={!!editResident}
          onOpenChange={(open) => !open && setEditResident(null)}
          title="Edit resident"
          description={`Update details for ${displayName(editResident)}.`}
          initialValues={{
            name: editResident.name ?? "",
            email: editResident.email ?? "",
            phone: editResident.phone ?? "",
            gender: editResident.gender ?? "",
            status: editResident.status ?? "",
          }}
          fields={formFields}
          onSubmit={(values) => handleUpdateResident({ ...editResident, ...values })}
          submitLabel="Save changes"
        />
      )}

      {/* Delete confirmation dialog */}
      <DeleteResidentDialog
        resident={deleteResident}
        displayName={displayName(deleteResident)}
        onOpenChange={(open) => !open && setDeleteResident(null)}
        onConfirm={handleConfirmDelete}
      />

      {/* Assign property dialog */}
      <AssignPropertyDialog
        resident={assignResident}
        properties={propertiesQuery.data}
        propertiesQuery={propertiesQuery}
        displayName={displayName(assignResident)}
        errorMessage={assignError}
        onOpenChange={(open) => {
          if (!open) {
            setAssignResident(null);
            setAssignError("");
          }
        }}
        onConfirm={handleConfirmAssign}
      />
    </div>
  );
}